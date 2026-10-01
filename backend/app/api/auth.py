from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import User
from app.schemas.auth import JobRoleBrief, LoginRequest, TokenResponse, UserOut
from app.security import create_access_token, verify_password
from app.services.access import allowed_types

router = APIRouter(prefix="/auth", tags=["auth"])

# Accounts are created by administrators on the Employees page; there is no
# public sign-up.


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        job_role=JobRoleBrief(id=user.job_role.id, name=user.job_role.name)
        if user.job_role
        else None,
        allowed_types=allowed_types(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "This account is disabled. Contact your administrator."
        )

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        user=user_out(user),
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return user_out(user)
