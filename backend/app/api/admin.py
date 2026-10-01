"""Employee management: job roles and the people who hold them.

Administrators only. A job role lists the output types its holders may create;
removing an employee is done by deactivating them, so their work and the audit
trail stay intact.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select

from app.api.auth import user_out
from app.api.deps import DbSession, require_role
from app.models import AuditLog, JobRole, User
from app.schemas.auth import (
    EmployeeIn,
    EmployeeUpdate,
    JobRoleIn,
    JobRoleOut,
    JobRoleUpdate,
    UserOut,
)
from app.security import hash_password
from app.services.generation.formats import FORMATS

router = APIRouter(prefix="/admin", tags=["employees"])

Admin = Annotated[User, Depends(require_role("admin"))]


def _check_types(types: list[str]) -> list[str]:
    unknown = [t for t in types if t not in FORMATS]
    if unknown:
        raise HTTPException(422, f"Unknown output type(s): {', '.join(unknown)}")
    # Keep catalog order and drop duplicates.
    return [key for key in FORMATS if key in set(types)]


async def _role_out(db: DbSession, role: JobRole) -> JobRoleOut:
    count = await db.scalar(select(func.count()).where(User.job_role_id == role.id))
    return JobRoleOut(
        id=role.id,
        name=role.name,
        description=role.description,
        allowed_types=list(role.allowed_types or []),
        employee_count=count or 0,
    )


async def _load_user(db: DbSession, user_id: uuid.UUID) -> User:
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(404, "Employee not found")
    return user


# --- job roles --------------------------------------------------------------


@router.get("/roles", response_model=list[JobRoleOut])
async def list_roles(db: DbSession, _: Admin) -> list[JobRoleOut]:
    roles = await db.scalars(select(JobRole).order_by(JobRole.name))
    return [await _role_out(db, r) for r in roles]


@router.post("/roles", response_model=JobRoleOut, status_code=201)
async def create_role(body: JobRoleIn, db: DbSession, admin: Admin) -> JobRoleOut:
    if await db.scalar(select(JobRole).where(func.lower(JobRole.name) == body.name.lower())):
        raise HTTPException(409, "A role with this name already exists")
    role = JobRole(
        name=body.name.strip(),
        description=body.description.strip(),
        allowed_types=_check_types(body.allowed_types),
    )
    db.add(role)
    await db.flush()
    db.add(AuditLog(actor_id=admin.id, entity="job_role", entity_id=role.id, action="create"))
    await db.commit()
    return await _role_out(db, role)


@router.patch("/roles/{role_id}", response_model=JobRoleOut)
async def update_role(
    role_id: uuid.UUID, body: JobRoleUpdate, db: DbSession, admin: Admin
) -> JobRoleOut:
    role = await db.get(JobRole, role_id)
    if role is None:
        raise HTTPException(404, "Role not found")
    if body.name is not None and body.name.strip() != role.name:
        clash = await db.scalar(
            select(JobRole).where(
                func.lower(JobRole.name) == body.name.strip().lower(), JobRole.id != role.id
            )
        )
        if clash:
            raise HTTPException(409, "A role with this name already exists")
        role.name = body.name.strip()
    if body.description is not None:
        role.description = body.description.strip()
    if body.allowed_types is not None:
        role.allowed_types = _check_types(body.allowed_types)
    db.add(AuditLog(actor_id=admin.id, entity="job_role", entity_id=role.id, action="update"))
    await db.commit()
    await db.refresh(role)
    return await _role_out(db, role)


@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(role_id: uuid.UUID, db: DbSession, admin: Admin) -> Response:
    role = await db.get(JobRole, role_id)
    if role is None:
        raise HTTPException(404, "Role not found")
    holders = await db.scalar(select(func.count()).where(User.job_role_id == role.id))
    if holders:
        raise HTTPException(
            409, f"{holders} employee(s) still have this role. Move them to another role first."
        )
    await db.delete(role)
    db.add(AuditLog(actor_id=admin.id, entity="job_role", entity_id=role_id, action="delete"))
    await db.commit()
    return Response(status_code=204)


# --- employees --------------------------------------------------------------


@router.get("/employees", response_model=list[UserOut])
async def list_employees(db: DbSession, _: Admin) -> list[UserOut]:
    users = await db.scalars(select(User).order_by(User.is_active.desc(), User.name))
    return [user_out(u) for u in users.unique()]


@router.post("/employees", response_model=UserOut, status_code=201)
async def create_employee(body: EmployeeIn, db: DbSession, admin: Admin) -> UserOut:
    email = body.email.lower()
    if await db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    if body.job_role_id and await db.get(JobRole, body.job_role_id) is None:
        raise HTTPException(422, "Role not found")
    user = User(
        email=email,
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        role=body.role,
        job_role_id=body.job_role_id,
    )
    db.add(user)
    await db.flush()
    new_id = user.id
    db.add(AuditLog(actor_id=admin.id, entity="user", entity_id=new_id, action="create"))
    await db.commit()
    return user_out(await _load_user(db, new_id))


@router.patch("/employees/{user_id}", response_model=UserOut)
async def update_employee(
    user_id: uuid.UUID, body: EmployeeUpdate, db: DbSession, admin: Admin
) -> UserOut:
    user = await _load_user(db, user_id)
    is_self = user.id == admin.id
    if is_self and (body.is_active is False or (body.role and body.role != "admin")):
        raise HTTPException(409, "You cannot disable yourself or remove your own admin access.")

    if body.name is not None:
        user.name = body.name.strip()
    if body.clear_job_role:
        user.job_role_id = None
    elif body.job_role_id is not None:
        if await db.get(JobRole, body.job_role_id) is None:
            raise HTTPException(422, "Role not found")
        user.job_role_id = body.job_role_id
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password:
        user.password_hash = hash_password(body.password)

    changed = sorted(k for k, v in body.model_dump(exclude={"password"}).items() if v)
    db.add(
        AuditLog(
            actor_id=admin.id,
            entity="user",
            entity_id=user.id,
            action="update",
            payload={"fields": changed, "password_reset": bool(body.password)},
        )
    )
    await db.commit()
    # Reload by the path id: attributes on `user` are expired after the commit.
    db.expire_all()
    return user_out(await _load_user(db, user_id))
