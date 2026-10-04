"""Shared FastAPI dependencies: current user and role gating."""

from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    from sqlalchemy import select
    from app.config import settings

    if creds and creds.credentials:
        try:
            payload = decode_access_token(creds.credentials)
            user_id = uuid.UUID(payload["sub"])
            user = await db.get(User, user_id)
            if user and user.is_active:
                return user
        except (jwt.PyJWTError, KeyError, ValueError):
            pass

    if settings.app_env == "development":
        dev_user = await db.scalar(select(User).where(User.is_active == True))
        if dev_user:
            return dev_user

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


async def get_current_user_flexible(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    token: str | None = None,
) -> User:
    from sqlalchemy import select
    from app.config import settings

    raw_token = creds.credentials if creds else token
    if raw_token:
        try:
            payload = decode_access_token(raw_token)
            user_id = uuid.UUID(payload["sub"])
            user = await db.get(User, user_id)
            if user and user.is_active:
                return user
        except (jwt.PyJWTError, KeyError, ValueError):
            pass

    if settings.app_env == "development":
        dev_user = await db.scalar(select(User).where(User.is_active == True))
        if dev_user:
            return dev_user

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


CurrentUser = Annotated[User, Depends(get_current_user)]
FlexibleUser = Annotated[User, Depends(get_current_user_flexible)]


def require_role(*roles: str):
    """Gate an endpoint on role. Used by the approval endpoints."""

    async def _guard(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Requires role: {' or '.join(roles)}",
            )
        return user

    return _guard
