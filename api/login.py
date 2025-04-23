from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import Member
from api.utils.auth_tools import create_tokens, decode_token, get_current_member

router = APIRouter()

class RegisterRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    phone: Optional[str] = None

class TelegramAuth(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

class RefreshRequest(BaseModel):
    refresh: str

@router.post("/member", response_model=dict)
async def login_via_telegram(
    data: TelegramAuth,
    db: AsyncSession = Depends(get_db),
):
    # TODO: проверка data.hash по инструкции Telegram
    q = await db.execute(select(Member).filter_by(telegram_id=data.id))
    user = q.scalars().first()
    if not user:
        user = Member(
            telegram_id=data.id,
            username=data.username,
            first_name=data.first_name,
        )
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
