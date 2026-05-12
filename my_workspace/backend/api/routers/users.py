"""Users router — CRUD user accounts (SUPERADMIN only)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.deps import CurrentUser, DBDep, require
from auth.password import hash_password
from models.user import User
from schemas.user import UserCreate, UserRead, UserUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead], dependencies=[require("users:read")])
async def list_users(db: DBDep) -> list[User]:
    result = await db.execute(select(User).order_by(User.id))
    return list(result.scalars().all())


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED,
             dependencies=[require("users:create")])
async def create_user(body: UserCreate, db: DBDep, user: CurrentUser) -> User:
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists")

    new_user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        role=body.role,
        display_name=body.display_name,
        camera_scope=body.camera_scope,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    await db.commit()
    logger.info("User created: username=%s role=%s by=%s", new_user.username, new_user.role, user.username)
    return new_user


@router.get("/{user_id}", response_model=UserRead, dependencies=[require("users:read")])
async def get_user(user_id: int, db: DBDep) -> User:
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return u


@router.patch("/{user_id}", response_model=UserRead, dependencies=[require("users:update")])
async def update_user(user_id: int, body: UserUpdate, db: DBDep, user: CurrentUser) -> User:
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(u, field, value)
    await db.commit()
    await db.refresh(u)
    logger.info("User %d updated by %s", user_id, user.username)
    return u


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[require("users:delete")])
async def delete_user(user_id: int, db: DBDep, user: CurrentUser) -> None:
    u = await db.get(User, user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if u.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete your own account")
    await db.delete(u)
    await db.commit()
    logger.info("User %d deleted by %s", user_id, user.username)
