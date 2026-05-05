"""The single abstraction around the LLM. All OpenAI calls live here.

Design:
- Always returns a Pydantic-validated object — never raw model output.
- Every call writes an AIInteractionLog row for audit.
- When OPENAI_LIVE=false (default), returns deterministic rule-based stubs so
  the whole product can be demoed / tested without an API key.
- Stubs are intentionally simple and conservative — they match the AI safety
  rules (prefer escalation on uncertainty).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.ai_log import AIInteractionLog
from app.models.faq import FAQEntry
from app.models.organization import OrgSettings
from app.prompts.system import (
    CLASSIFY_INSTRUCTIONS,
    DRAFT_INSTRUCTIONS,
    EXTRACT_INSTRUCTIONS,
    PROMPT_VERSION,
    SYSTEM_GUARDRAILS,
)
from app.schemas.ai import (
    ClassificationResult,
    DraftResult,
    ExtractionResult,
)
from app.services.rules_engine import apply_rules
from app.services.treatment_normalizer import normalize_treatment

log = get_logger(__name__)
settings = get_settings()


@dataclass
class OrgContext:
    organization_id: UUID
    brand_name: str
    tone_of_voice: str
    disclaimers: str
    escalation_message: str
    faqs: list[FAQEntry]


def load_org_context(db: Session, organization_id: UUID) -> OrgContext:
    org_settings = db.execute(
        select(OrgSettings).where(OrgSettings.organization_id == organization_id)
    ).scalar_one_or_none()
    faqs = (
        db.execute(
            select(FAQEntry)
            .where(FAQEntry.organization_id == organization_id)
            .where(FAQEntry.is_active.is_(True))
            .order_by(FAQEntry.priority.asc())
        )
        .scalars()
        .all()
    )
    return OrgContext(
        organization_id=organization_id,
        brand_name=org_settings.brand_name if org_settings else "the spa",
        tone_of_voice=org_settings.tone_of_voice if org_settings else "",
        disclaimers=org_settings.disclaimers if org_settings else "",
        escalation_message=(
            org_settings.escalation_message
            if org_settings
            else "Thanks for your message. I'm flagging this for our team."
        ),
        faqs=faqs,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_message(
    db: Session,
    organization_id: UUID,
    message: str,
    conversation_id: Optional[UUID] = None,
    lead_id: Optional[UUID] = None,
) -> ClassificationResult:
    if settings.openai_live and settings.openai_api_key:
        result = _classify_live(message)
    else:
        result = _classify_stub(message)
    _log_ai(
        db,
        organization_id=organization_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        task="classify",
        input_text=message,
        output=result.model_dump(),
        success=True,
    )
    return result


def extract_lead_info(
    db: Session,
    organization_id: UUID,
    message: str,
    conversation_id: Optional[UUID] = None,
    lead_id: Optional[UUID] = None,
) -> ExtractionResult:
    if settings.openai_live and settings.openai_api_key:
        result = _extract_live(message)
    else:
        result = _extract_stub(message)
    _log_ai(
        db,
        organization_id=organization_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        task="extract",
        input_text=message,
        output=result.model_dump(),
        success=True,
    )
    return result


def draft_reply(
    db: Session,
    organization_id: UUID,
    message: str,
    classification: ClassificationResult,
    conversation_id: Optional[UUID] = None,
    lead_id: Optional[UUID] = None,
) -> DraftResult:
    ctx = load_org_context(db, organization_id)
    if settings.openai_live and settings.openai_api_key:
        result = _draft_live(message, ctx, classification)
    else:
        result = _draft_stub(message, ctx, classification)
    _log_ai(
        db,
        organization_id=organization_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        task="draft_reply",
        input_text=message,
        output=result.model_dump(),
        success=True,
    )
    return result


# ---------------------------------------------------------------------------
# Live (OpenAI) implementations
# ---------------------------------------------------------------------------


def _openai_client():
    # Lazy import so the package isn't required when OPENAI_LIVE=false.
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


def _call_openai_json(system: str, user: str, schema_cls: type[BaseModel]) -> BaseModel:
    client = _openai_client()
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    text = completion.choices[0].message.content or "{}"
    try:
        data = json.loads(text)
        return schema_cls.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        log.warning("ai_invalid_output", err=str(exc), raw=text[:400])
        raise


def _classify_live(message: str) -> ClassificationResult:
    try:
        return _call_openai_json(
            SYSTEM_GUARDRAILS + "\n" + CLASSIFY_INSTRUCTIONS,
            f"Message:\n{message}",
            ClassificationResult,
        )
    except Exception:
        return _classify_stub(message)


def _extract_live(message: str) -> ExtractionResult:
    try:
        return _call_openai_json(
            SYSTEM_GUARDRAILS + "\n" + EXTRACT_INSTRUCTIONS,
            f"Message:\n{message}",
            ExtractionResult,
        )
    except Exception:
        return _extract_stub(message)


def _draft_live(
    message: str, ctx: OrgContext, classification: ClassificationResult
) -> DraftResult:
    faq_block = _render_faq_block(ctx.faqs)
    user_prompt = (
        f"BRAND: {ctx.brand_name}\n"
        f"TONE: {ctx.tone_of_voice}\n"
        f"APPROVED_FAQS:\n{faq_block}\n\n"
        f"CLASSIFICATION: {classification.model_dump()}\n\n"
        f"INBOUND_MESSAGE:\n{message}\n"
    )
    try:
        return _call_openai_json(
            SYSTEM_GUARDRAILS + "\n" + DRAFT_INSTRUCTIONS,
            user_prompt,
            DraftResult,
        )
    except Exception:
        return _draft_stub(message, ctx, classification)


def _render_faq_block(faqs: list[FAQEntry]) -> str:
    if not faqs:
        return "(no approved FAQs — escalate factual questions)"
    lines = []
    for i, f in enumerate(faqs, 1):
        lines.append(f"{i}. [{f.category}] Q: {f.question}\n   A: {f.answer}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Offline stubs — deterministic, conservative, used when OPENAI_LIVE=false
# ---------------------------------------------------------------------------


def _classify_stub(message: str) -> ClassificationResult:
    rule = apply_rules(message)
    lower = (message or "").lower()

    if rule.needs_escalation:
        intent = (
            "medical_concern"
            if rule.escalation_reason and "medical" in rule.escalation_reason
            else "complaint"
            if rule.escalation_reason and "complaint" in rule.escalation_reason
            else "existing_appointment"
            if rule.existing_appointment
            else "human_request"
        )
        return ClassificationResult(
            intent=intent,
            urgency="high",
            needs_escalation=True,
            escalation_reason=rule.escalation_reason,
            confidence=0.9,
            treatment_interest=normalize_treatment(message),
        )

    if any(w in lower for w in ("book", "schedule", "appointment")):
        intent = "booking"
    elif any(w in lower for w in ("price", "cost", "how much", "pricing")):
        intent = "pricing"
    elif any(w in lower for w in ("available", "availability", "next week", "tomorrow")):
        intent = "availability"
    elif normalize_treatment(message):
        intent = "treatment_info"
    else:
        intent = "general_question"

    return ClassificationResult(
        intent=intent,  # type: ignore[arg-type]
        urgency="medium" if rule.urgent else "low",
        needs_escalation=False,
        escalation_reason=None,
        confidence=0.6,
        treatment_interest=normalize_treatment(message),
    )


def _extract_stub(message: str) -> ExtractionResult:
    return ExtractionResult(treatment_interest=normalize_treatment(message))


def _draft_stub(
    message: str, ctx: OrgContext, classification: ClassificationResult
) -> DraftResult:
    brand = ctx.brand_name
    treatment_key = classification.treatment_interest or normalize_treatment(message)

    if classification.needs_escalation:
        return DraftResult(
            reply_text=ctx.escalation_message or (
                "Thanks for your message. I'm flagging this for our team now so "
                "they can help you directly as soon as possible."
            ),
            should_escalate=True,
            escalation_reason=classification.escalation_reason,
        )

    # Try FAQ match
    faq = _best_faq_match(ctx.faqs, message)
    if faq:
        return DraftResult(
            reply_text=faq.answer,
            should_send_booking_link=classification.intent in (
                "pricing",
                "treatment_info",
                "booking",
                "availability",
            ),
            booking_route_key=treatment_key,
        )

    if classification.intent == "booking":
        return DraftResult(
            reply_text=(
                f"Happy to help you book at {brand}. What treatment are you "
                "interested in?"
            ),
            should_send_booking_link=bool(treatment_key),
            booking_route_key=treatment_key,
            ask_followup_question=not bool(treatment_key),
            followup_question=(
                "Which treatment did you have in mind?" if not treatment_key else None
            ),
        )

    if not treatment_key:
        return DraftResult(
            reply_text=(
                f"Thanks for reaching out to {brand}. I can help with treatment "
                "questions, pricing, availability, or booking. What treatment "
                "are you interested in?"
            ),
            ask_followup_question=True,
            followup_question="What treatment are you interested in?",
        )

    # We know the treatment but have no FAQ — safe fallback: offer booking, avoid inventing
    return DraftResult(
        reply_text=(
            f"Thanks for your interest in {brand}. I can share a little more "
            "and send you a booking link to chat with our team."
        ),
        should_send_booking_link=True,
        booking_route_key=treatment_key,
    )


def _best_faq_match(faqs: list[FAQEntry], message: str) -> Optional[FAQEntry]:
    if not faqs:
        return None
    tokens = _tokens(message)
    if not tokens:
        return None

    best: Optional[FAQEntry] = None
    best_score = 0
    for f in faqs:
        q_tokens = _tokens(f.question)
        overlap = len(tokens & q_tokens)
        if f.tags:
            tag_tokens = {str(t).lower() for t in f.tags}
            overlap += len(tokens & tag_tokens)
        # simple substring bonus
        if any(t in message.lower() for t in q_tokens if len(t) > 4):
            overlap += 1
        if overlap > best_score:
            best_score = overlap
            best = f
    return best if best_score >= 2 else None


def _tokens(text: str) -> set[str]:
    return {t for t in "".join(c if c.isalnum() else " " for c in text.lower()).split() if len(t) > 2}


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


def _log_ai(
    db: Session,
    *,
    organization_id: UUID,
    conversation_id: Optional[UUID],
    lead_id: Optional[UUID],
    task: str,
    input_text: str,
    output: dict[str, Any],
    success: bool,
    error: Optional[str] = None,
) -> None:
    entry = AIInteractionLog(
        organization_id=organization_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        task_type=task,
        input_text=input_text,
        output_json=output,
        prompt_version=PROMPT_VERSION,
        model_name=settings.openai_model if settings.openai_live else "stub",
        success=success,
        error_message=error,
    )
    db.add(entry)
