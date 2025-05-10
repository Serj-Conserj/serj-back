from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import Member
from api.utils.auth_tools import (
    create_tokens,
    decode_token,
    get_current_member,
    parse_validate_raw,
    validate_web_app_data,
    verify_telegram_auth,
)
from api.utils.schemas import TelegramAuth, RefreshRequest

router = APIRouter()


@router.post("/member", response_model=dict)
async def login_via_telegram(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    if "init_data" in payload:

        raw = validate_web_app_data(payload.get("init_data"))
        validated = parse_validate_raw(raw)
        user_data = validated["user"]
        ta = TelegramAuth(**user_data)
    else:
        ta = TelegramAuth(**payload)

    telegram_id = ta.id

    q = await db.execute(select(Member).filter_by(telegram_id=telegram_id))
    user = q.scalars().first()
    if not user:
        user = Member(
            telegram_id=telegram_id,
            username=ta.username,
            first_name=ta.first_name,
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


@router.get("/member_phone")
async def get_all_bookings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_member),
):
    result = await db.execute(select(Member.phone).where(Member.id == current_user.id))
    phone = result.scalar_one_or_none()
    return phone
