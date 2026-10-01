from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

AccessLevel = Literal["editor", "approver", "admin"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class JobRoleBrief(BaseModel):
    id: uuid.UUID
    name: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    role: AccessLevel
    is_active: bool = True
    created_at: datetime
    job_role: JobRoleBrief | None = None
    # Output types this person may create, decided by their job role.
    allowed_types: list[str] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- employee management (administrators only) ---------------------------------


class JobRoleIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    allowed_types: list[str] = Field(default_factory=list)


class JobRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    allowed_types: list[str] | None = None


class JobRoleOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    allowed_types: list[str]
    employee_count: int = 0


class EmployeeIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    job_role_id: uuid.UUID | None = None
    role: AccessLevel = "editor"


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    job_role_id: uuid.UUID | None = None
    # Set true to remove the job role (job_role_id=None alone means "unchanged").
    clear_job_role: bool = False
    role: AccessLevel | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
