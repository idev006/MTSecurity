"""LPR router — manage license plate whitelist."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require
from models.lpr_whitelist import LPRWhitelist
from pydantic import BaseModel, Field

router = APIRouter(prefix="/lpr", tags=["lpr"])

class LPRCreate(BaseModel):
    plate: str = Field(..., max_length=32)
    owner_name: str | None = Field(None, max_length=128)
    description: str | None = None
    is_active: bool = True

class LPRRead(LPRCreate):
    id: int

@router.get("/", response_model=list[LPRRead])
async def list_lpr(
    db: AsyncSession = Depends(get_db),
    current_user=require("cameras:read"), # Minimal perm to see whitelist
):
    result = await db.execute(select(LPRWhitelist).order_by(LPRWhitelist.plate))
    return result.scalars().all()

@router.post("/", response_model=LPRRead, status_code=status.HTTP_201_CREATED)
async def create_lpr(
    body: LPRCreate,
    db: AsyncSession = Depends(get_db),
    current_user=require("users:manage"), # Only admins can manage
):
    # Check if plate already exists
    existing = await db.execute(select(LPRWhitelist).where(LPRWhitelist.plate == body.plate))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="License plate already in whitelist")

    lpr = LPRWhitelist(**body.model_dump())
    db.add(lpr)
    await db.commit()
    await db.refresh(lpr)
    return lpr

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lpr(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=require("users:manage"),
):
    lpr = await db.get(LPRWhitelist, id)
    if not lpr:
        raise HTTPException(status_code=404, detail="Not found")
    
    await db.delete(lpr)
    await db.commit()
