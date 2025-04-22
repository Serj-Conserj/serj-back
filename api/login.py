from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import Member
from api.utils.auth_tools import create_tokens, decode_token, get_current_member

router = APIRouter(
    prefix="/api/member",
    tags=["member"],
)

class RegisterRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    phone: Optional[str] = None

class RefreshRequest(BaseModel):
    refresh: str

@router.post("", response_model=dict)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(Member).filter_by(telegram_id=req.telegram_id))
    user = q.scalars().first()
    if not user:
        user = Member(**req.dict())
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return create_tokens(user.id, user.telegram_id)

@router.post("/refresh", response_model=dict)
async def refresh_token(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    data = decode_token(req.refresh)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = await db.get(Member, data["id"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return create_tokens(user.id, user.telegram_id)

@router.get("/protected")
async def protected_route(current: Member = Depends(get_current_member)):
    return {"msg": f"Hello, {current.username or current.first_name}!"}
