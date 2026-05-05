from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: DbSession) -> LoginResponse:
    user = db.execute(select(User).where(User.email == str(payload.email))).scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")

    token = create_access_token(
        subject=str(user.id),
        extra={"org": str(user.organization_id), "role": user.role},
    )
    response.set_cookie(
        settings.access_token_cookie_name,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=settings.jwt_expires_minutes * 60,
        path="/",
    )
    return LoginResponse(access_token=token)


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(settings.access_token_cookie_name, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser) -> MeResponse:
    return MeResponse.model_validate(user)
