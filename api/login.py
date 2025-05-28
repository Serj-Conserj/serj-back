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
)
from api.utils.schemas import TelegramAuth, RefreshRequest
from api.utils.logger import logger  # ✅ логгер

router = APIRouter()


@router.post("/member", response_model=dict)
async def login_via_telegram(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        if "init_data" in payload:
            raw = validate_web_app_data(payload.get("init_data"))
            validated = parse_validate_raw(raw)
            user_data = validated["user"]
            ta = TelegramAuth(**user_data)
        else:
            ta = TelegramAuth(**payload)

        telegram_id = ta.id
        logger.info(f"📲 Авторизация Telegram ID: {telegram_id}")

        q = await db.execute(select(Member).filter_by(telegram_id=telegram_id))
        user = q.scalars().first()

        if not user:
            logger.info(f"🆕 Новый пользователь: {ta.username or ta.first_name}")
            user = Member(
                telegram_id=telegram_id,
                username=ta.username,
                first_name=ta.first_name,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        return create_tokens(user.id, user.telegram_id)

    except Exception as e:
        logger.error(f"❌ Ошибка авторизации: {e}")
        raise HTTPException(status_code=400, detail="Ошибка авторизации")


@router.post("/refresh", response_model=dict)
async def refresh_token(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.info("🔄 Обновление refresh токена")
    data = decode_token(req.refresh)
    if not data:
        logger.warning("⚠️ Невалидный refresh токен")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    user = await db.get(Member, data["id"])
    if not user:
        logger.warning(f"❗ Пользователь с ID {data['id']} не найден")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return create_tokens(user.id, user.telegram_id)


@router.get("/protected")
async def protected_route(current: Member = Depends(get_current_member)):
    logger.info(f"🛡️ Доступ к защищённому маршруту: {current.id}")
    return {"msg": f"Hello, {current.username or current.first_name}!"}


@router.get("/member_phone")
async def get_all_bookings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_member),
):
    logger.info(f"📞 Запрос телефона участника {current_user.id}")
    result = await db.execute(select(Member.phone).where(Member.id == current_user.id))
    phone = result.scalar_one_or_none()
    return phone
