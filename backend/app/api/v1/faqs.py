from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.faq import FAQEntry
from app.schemas.faq import FAQCreate, FAQOut, FAQUpdate

router = APIRouter(prefix="/faqs", tags=["faqs"])


@router.get("", response_model=list[FAQOut])
def list_faqs(db: DbSession, user: CurrentUser) -> list[FAQOut]:
    rows = db.execute(
        select(FAQEntry)
        .where(FAQEntry.organization_id == user.organization_id)
        .order_by(FAQEntry.priority.asc(), FAQEntry.category.asc())
    ).scalars().all()
    return [FAQOut.model_validate(r) for r in rows]


@router.post("", response_model=FAQOut, status_code=status.HTTP_201_CREATED)
def create_faq(payload: FAQCreate, db: DbSession, user: CurrentUser) -> FAQOut:
    row = FAQEntry(
        organization_id=user.organization_id,
        **payload.model_dump(exclude_none=True),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return FAQOut.model_validate(row)


@router.patch("/{faq_id}", response_model=FAQOut)
def update_faq(faq_id: UUID, payload: FAQUpdate, db: DbSession, user: CurrentUser) -> FAQOut:
    row = db.get(FAQEntry, faq_id)
    if not row or row.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "FAQ not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return FAQOut.model_validate(row)


@router.delete("/{faq_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_faq(faq_id: UUID, db: DbSession, user: CurrentUser) -> Response:
    row = db.get(FAQEntry, faq_id)
    if not row or row.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "FAQ not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
