from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, Message
from app.models.lead import Lead
from app.schemas.common import Page
from app.schemas.conversation import (
    ConversationDetail,
    ConversationListItem,
    ConversationOut,
    MessageCreate,
    MessageOut,
)
from app.schemas.lead import LeadOut
from app.services import ai_service
from app.services.escalation_service import escalate as escalate_conversation
from app.services.followup_service import cancel_pending_followups
from app.services.message_service import send_manual_reply
from pydantic import BaseModel, Field

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=Page[ConversationListItem])
def list_conversations(
    db: DbSession,
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    escalated: Optional[bool] = None,
    limit: int = Query(50, le=200, ge=1),
    offset: int = Query(0, ge=0),
) -> Page[ConversationListItem]:
    stmt = select(Conversation).where(Conversation.organization_id == user.organization_id)
    count_stmt = select(func.count(Conversation.id)).where(
        Conversation.organization_id == user.organization_id
    )
    if status_filter:
        stmt = stmt.where(Conversation.status == status_filter)
        count_stmt = count_stmt.where(Conversation.status == status_filter)
    if escalated is True:
        stmt = stmt.where(Conversation.escalation_state == "escalated")
        count_stmt = count_stmt.where(Conversation.escalation_state == "escalated")

    total = db.execute(count_stmt).scalar_one()
    convs = db.execute(stmt.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)).scalars().all()

    items: list[ConversationListItem] = []
    for c in convs:
        lead = db.get(Lead, c.lead_id)
        last = db.execute(
            select(Message)
            .where(Message.conversation_id == c.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        ).scalars().first()
        items.append(
            ConversationListItem(
                id=c.id,
                organization_id=c.organization_id,
                lead_id=c.lead_id,
                channel_type=c.channel_type,
                status=c.status,
                ai_enabled=c.ai_enabled,
                escalation_state=c.escalation_state,
                ai_mode=c.ai_mode,
                created_at=c.created_at,
                updated_at=c.updated_at,
                lead_name=(lead.full_name or lead.first_name) if lead else None,
                lead_phone=lead.phone if lead else None,
                last_message_preview=(last.content[:140] if last else None),
                last_message_at=(last.created_at if last else None),
                unread_from_lead=(last is not None and last.direction == "inbound"),
            )
        )
    return Page[ConversationListItem](items=items, total=total, limit=limit, offset=offset)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: UUID, db: DbSession, user: CurrentUser) -> ConversationDetail:
    c = db.get(Conversation, conversation_id)
    if not c or c.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    lead = db.get(Lead, c.lead_id)
    msgs = db.execute(
        select(Message)
        .where(Message.conversation_id == c.id)
        .order_by(Message.created_at.asc())
    ).scalars().all()
    return ConversationDetail(
        **ConversationOut.model_validate(c).model_dump(),
        lead=LeadOut.model_validate(lead),
        messages=[MessageOut.model_validate(m) for m in msgs],
    )


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=201)
def post_message(
    conversation_id: UUID,
    payload: MessageCreate,
    db: DbSession,
    user: CurrentUser,
) -> MessageOut:
    c = db.get(Conversation, conversation_id)
    if not c or c.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    lead = db.get(Lead, c.lead_id)
    if not lead:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")
    msg = send_manual_reply(
        db,
        organization_id=user.organization_id,
        conversation=c,
        lead=lead,
        content=payload.content,
        channel_type=payload.channel_type,
        actor_user_id=user.id,
    )
    db.commit()
    db.refresh(msg)
    return MessageOut.model_validate(msg)


@router.post("/{conversation_id}/takeover", response_model=ConversationOut)
def takeover(conversation_id: UUID, db: DbSession, user: CurrentUser) -> ConversationOut:
    c = db.get(Conversation, conversation_id)
    if not c or c.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    c.ai_enabled = False
    c.status = "waiting_on_staff"
    db.add(c)
    db.add(
        AuditLog(
            organization_id=c.organization_id,
            actor_user_id=user.id,
            actor_type="user",
            action="ai_takeover",
            entity_type="conversation",
            entity_id=c.id,
        )
    )
    db.commit()
    db.refresh(c)
    return ConversationOut.model_validate(c)


@router.post("/{conversation_id}/release-ai", response_model=ConversationOut)
def release_ai(conversation_id: UUID, db: DbSession, user: CurrentUser) -> ConversationOut:
    c = db.get(Conversation, conversation_id)
    if not c or c.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    c.ai_enabled = True
    c.status = "open"
    c.escalation_state = "resolved" if c.escalation_state == "escalated" else c.escalation_state
    db.add(c)
    db.add(
        AuditLog(
            organization_id=c.organization_id,
            actor_user_id=user.id,
            actor_type="user",
            action="ai_release",
            entity_type="conversation",
            entity_id=c.id,
        )
    )
    db.commit()
    db.refresh(c)
    return ConversationOut.model_validate(c)


@router.post("/{conversation_id}/mark-booked", response_model=ConversationOut)
def mark_booked(conversation_id: UUID, db: DbSession, user: CurrentUser) -> ConversationOut:
    c = db.get(Conversation, conversation_id)
    if not c or c.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    lead = db.get(Lead, c.lead_id)
    if lead:
        lead.status = "booked"
        lead.booking_status = "booked"
        cancel_pending_followups(db, lead.id)
        db.add(lead)
    c.status = "closed"
    db.add(c)
    db.add(
        AuditLog(
            organization_id=c.organization_id,
            actor_user_id=user.id,
            actor_type="user",
            action="mark_booked",
            entity_type="conversation",
            entity_id=c.id,
        )
    )
    db.commit()
    db.refresh(c)
    return ConversationOut.model_validate(c)


class EscalatePayload(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=200)


@router.post("/{conversation_id}/escalate", response_model=ConversationOut)
def escalate_endpoint(
    conversation_id: UUID,
    payload: EscalatePayload,
    db: DbSession,
    user: CurrentUser,
) -> ConversationOut:
    """Manual escalation from the inbox. Reuses the same service that rules
    and AI escalation go through, so notifications + audit stay consistent."""
    c = db.get(Conversation, conversation_id)
    if not c or c.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    lead = db.get(Lead, c.lead_id)
    if not lead:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")
    escalate_conversation(
        db,
        organization_id=c.organization_id,
        conversation=c,
        lead=lead,
        reason=f"manual:{payload.reason}" if payload.reason else "manual",
    )
    cancel_pending_followups(db, lead.id)
    db.add(
        AuditLog(
            organization_id=c.organization_id,
            actor_user_id=user.id,
            actor_type="user",
            action="manual_escalate",
            entity_type="conversation",
            entity_id=c.id,
            audit_metadata={"reason": payload.reason} if payload.reason else None,
        )
    )
    db.commit()
    db.refresh(c)
    return ConversationOut.model_validate(c)


class MarkLostPayload(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=200)


from app.models.faq import FAQEntry


class ImproveReplyPayload(BaseModel):
    correction: str = Field(..., min_length=1, max_length=2000)


@router.post(
    "/{conversation_id}/messages/{message_id}/improve-reply",
    status_code=201,
)
def improve_reply(
    conversation_id: UUID,
    message_id: UUID,
    payload: ImproveReplyPayload,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    c = db.get(Conversation, conversation_id)
    if not c or c.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    bad = db.get(Message, message_id)
    if not bad or bad.conversation_id != c.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found")

    # Find the inbound message immediately preceding the AI reply.
    prior = db.execute(
        select(Message)
        .where(Message.conversation_id == c.id)
        .where(Message.created_at < bad.created_at)
        .where(Message.direction == "inbound")
        .order_by(Message.created_at.desc())
        .limit(1)
    ).scalars().first()
    question = (prior.content if prior else bad.content)[:500]

    faq = FAQEntry(
        organization_id=user.organization_id,
        category="staff_correction",
        question=question,
        answer=payload.correction.strip(),
        is_active=True,
        priority=1,  # sort first
    )
    db.add(faq)
    db.add(
        AuditLog(
            organization_id=user.organization_id,
            actor_user_id=user.id,
            actor_type="user",
            action="faq_correction_added",
            entity_type="message",
            entity_id=bad.id,
        )
    )
    db.commit()
    db.refresh(faq)
    return {"faq_id": str(faq.id)}


@router.post("/{conversation_id}/mark-lost", response_model=ConversationOut)
def mark_lost(
    conversation_id: UUID,
    payload: MarkLostPayload,
    db: DbSession,
    user: CurrentUser,
) -> ConversationOut:
    c = db.get(Conversation, conversation_id)
    if not c or c.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    lead = db.get(Lead, c.lead_id)
    if lead:
        lead.status = "closed_lost"
        if lead.booking_status not in ("booked",):
            lead.booking_status = "declined"
        cancel_pending_followups(db, lead.id)
        db.add(lead)
    c.status = "closed"
    c.ai_enabled = False
    db.add(c)
    db.add(
        AuditLog(
            organization_id=c.organization_id,
            actor_user_id=user.id,
            actor_type="user",
            action="mark_lost",
            entity_type="conversation",
            entity_id=c.id,
            audit_metadata={"reason": payload.reason} if payload.reason else None,
        )
    )
    db.commit()
    db.refresh(c)
    return ConversationOut.model_validate(c)
