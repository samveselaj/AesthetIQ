from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_role
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.auth import MeResponse

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = UserRole.STAFF.value


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


@router.get("", response_model=list[MeResponse])
def list_users(db: DbSession, user: CurrentUser) -> list[MeResponse]:
    rows = db.execute(
        select(User)
        .where(User.organization_id == user.organization_id)
        .order_by(User.created_at.asc())
    ).scalars().all()
    return [MeResponse.model_validate(r) for r in rows]


@router.post(
    "",
    response_model=MeResponse,
    status_code=201,
    dependencies=[Depends(require_role(UserRole.SPA_ADMIN, UserRole.SUPER_ADMIN))],
)
def create_user(payload: UserCreate, db: DbSession, user: CurrentUser) -> MeResponse:
    exists = db.execute(select(User).where(User.email == str(payload.email))).scalar_one_or_none()
    if exists:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already exists")
    new = User(
        organization_id=user.organization_id,
        full_name=payload.full_name,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(new)
    db.commit()
    db.refresh(new)
    return MeResponse.model_validate(new)


@router.patch(
    "/{user_id}",
    response_model=MeResponse,
    dependencies=[Depends(require_role(UserRole.SPA_ADMIN, UserRole.SUPER_ADMIN))],
)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DbSession,
    user: CurrentUser,
) -> MeResponse:
    row = db.get(User, user_id)
    if not row or row.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return MeResponse.model_validate(row)
