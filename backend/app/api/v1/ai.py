"""Internal AI endpoints — handy for inbox 'regenerate draft' + for test harnesses."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.ai import (
    ClassificationResult,
    ClassifyRequest,
    DraftRequest,
    DraftResult,
)
from app.services import ai_service

router = APIRouter(prefix="/internal/ai", tags=["ai"])


@router.post("/classify", response_model=ClassificationResult)
def classify(
    payload: ClassifyRequest, db: DbSession, user: CurrentUser
) -> ClassificationResult:
    result = ai_service.classify_message(
        db, organization_id=user.organization_id, message=payload.message
    )
    db.commit()
    return result


@router.post("/draft-reply", response_model=DraftResult)
def draft_reply(payload: DraftRequest, db: DbSession, user: CurrentUser) -> DraftResult:
    classification = ai_service.classify_message(
        db, organization_id=user.organization_id, message=payload.message
    )
    draft = ai_service.draft_reply(
        db,
        organization_id=user.organization_id,
        message=payload.message,
        classification=classification,
    )
    db.commit()
    return draft
