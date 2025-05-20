import aiohttp
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Union, List
from uuid import UUID
from datetime import datetime
import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from aio_pika import connect_robust, Message
import json

from database.database import get_db, AsyncSession
from database.models import Booking, Place, Member
from api.utils.auth_tools import get_current_member
from config import (
    rabbitmq_url,
    CALL_QUEUE,
    PARS_QUEUE,
    telegram_token,
    booking_failure_state,
    booking_success_state,
)
from api.utils.logger import logger  # ✅ логгер

router = APIRouter()


async def put_into_queue(booking_id: UUID, available_online: bool):
    queue_name = PARS_QUEUE if available_online else CALL_QUEUE
    logger.info(f"📤 Отправка booking_id={booking_id} в очередь {queue_name}")

    try:
        conn = await connect_robust(rabbitmq_url)
        channel = await conn.channel()
        await channel.set_qos(prefetch_count=1)
        await channel.declare_queue(queue_name, durable=True)

        body = json.dumps({"booking_id": str(booking_id)})
        await channel.default_exchange.publish(
            Message(body.encode(), content_type="application/json"),
            routing_key=queue_name,
        )
        await conn.close()
        logger.info("✅ Успешно отправлено в очередь")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке в очередь: {e}")
        raise


class BookingCreate(BaseModel):
    place_id: Union[str, UUID]
    booking_date: datetime
    num_of_people: int
    special_requests: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/bookings")
async def create_booking(
    booking: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Member = Depends(get_current_member),
):
    logger.info(f"📥 Новое бронирование от пользователя {current_user.id}")

    try:
        result = await db.execute(select(Place).where(Place.id == booking.place_id))
        place = result.scalars().first()
        if not place:
            logger.warning(f"❗ Место не найдено: {booking.place_id}")
            raise HTTPException(status_code=404, detail="Place not found")

        db_booking = Booking(
            id=uuid.uuid4(),
            user_id=current_user.id,
            place_id=booking.place_id,
            booking_date=booking.booking_date,
            num_of_people=booking.num_of_people,
            special_requests=booking.special_requests,
            status=0,
        )

        db.add(db_booking)
        await db.commit()
        await db.refresh(db_booking)

        logger.info(f"✅ Бронирование создано: {db_booking.id}")
        await put_into_queue(db_booking.id, place.available_online)

        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Бронирование успешно создано"},
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Ошибка при создании бронирования: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ----- Response Schemas -----
class MemberResponse(BaseModel):
    id: uuid.UUID
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    phone: Optional[str]
    is_admin: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class MetroStationResponse(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class CuisineResponse(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class PlaceResponse(BaseModel):
    id: UUID
    name: str
    available_online: bool
    metro_stations: List[MetroStationResponse] = []
    cuisines: List[CuisineResponse] = []
    address: Optional[str]

    class Config:
        from_attributes = True


class BookingResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    place_id: uuid.UUID
    booking_date: datetime
    recording_date: datetime
    num_of_people: int
    special_requests: Optional[str]
    # confirmed: bool
    status: int
    member: MemberResponse
    place: PlaceResponse

    class Config:
        json_encoders = {uuid.UUID: lambda x: str(x)}
        from_attributes = True


@router.get("/bookings")
async def get_all_bookings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_member),
):
    try:
        logger.info(f"📄 Получение бронирований для пользователя {current_user.id}")

        stmt = (
            select(Booking)
            .where(Booking.user_id == current_user.id)
            .options(
                selectinload(Booking.member),
                selectinload(Booking.place).options(
                    selectinload(Place.metro_stations),
                    selectinload(Place.cuisines),
                ),
            )
        )

        result = await db.execute(stmt)
        bookings = result.scalars().all()

        now = datetime.utcnow()
        upcoming_bookings, past_bookings, archived_bookings = [], [], []

        for booking in bookings:
            serialized = BookingResponse.from_orm(booking).dict()
            if booking.booking_date < now:
                archived_bookings.append(serialized)
            elif booking.staus == 0:
                past_bookings.append(serialized)
            else:
                upcoming_bookings.append(serialized)

        logger.info(f"✅ Найдено {len(bookings)} бронирований")
        return {
            "upcoming_bookings": upcoming_bookings,
            "past_bookings": past_bookings,
            "archived_bookings": archived_bookings,
        }

    except Exception as e:
        logger.error(f"❌ Ошибка при получении бронирований: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BookingStatusUpdate(BaseModel):
    booking_id: UUID
    status: str

    class Config:
        from_attributes = True


async def send_telegram_message(chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                response_text = await resp.text()
                raise Exception(
                    f"Ошибка отправки в Telegram: {resp.status} - {response_text}"
                )


@router.post("/bookings/update_status")
async def update_booking_status(
    data: BookingStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"🔄 Обновление статуса брони {data.booking_id} → {data.status}")
    try:
        result = await db.execute(
            select(Booking)
            .options(joinedload(Booking.member), joinedload(Booking.place))
            .where(Booking.id == data.booking_id)
        )
        booking = result.scalars().first()

        if not booking:
            logger.warning(f"❗ Бронь не найдена: {data.booking_id}")
            raise HTTPException(status_code=404, detail="Booking not found")

        short_id = str(booking.id)[-4:]

        if data.status == booking_success_state:
            booking.status = 1
            user_message = (
                f"✅ Успешно забронировали для вас место!\n\n"
                f"🏷 {booking.place.full_name}\n"
                f"🗓 {booking.booking_date.strftime('%d.%m.%Y в %H:%M')}\n"
                f"👥 {booking.num_of_people} чел.\n"
                f"📍 {booking.place.address}\n"
                f"🔢 Код брони: #{short_id}\n\n"
                f"Ждём вас! 🎉"
            )
        elif data.status == booking_failure_state:
            booking.status = 2
            user_message = (
                f"❌ К сожалению, не удалось забронировать для вас место в {booking.place.full_name}"
                f"на {booking.booking_date.strftime('%d.%m.%Y в %H:%M')}.\n"
                "Попробуйте другое время или место."
            )
        else:
            logger.warning("⚠️ Некорректный статус: %s", data.status)
            raise HTTPException(status_code=400, detail="Invalid status value")

        await db.commit()
        await db.refresh(booking)

        try:
            await send_telegram_message(
                booking.member.telegram_id, user_message
            )
            logger.info(f"📩 Уведомление отправлено Telegram ID {booking.member.telegram_id}")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка отправки сообщения Telegram: {e}")

        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Booking status updated"},
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Ошибка обновления статуса бронирования: {e}")
        raise HTTPException(status_code=500, detail=str(e))
