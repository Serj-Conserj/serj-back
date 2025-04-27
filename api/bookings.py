from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Union, List
from uuid import UUID
from datetime import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.database import get_db, AsyncSession
from database.models import Booking, Place, Member
from api.utils.auth_tools import get_current_member

from config import rabbitmq_url, CALL_QUEUE, PARS_QUEUE
from aio_pika import connect_robust, Message
import json

router = APIRouter()


async def put_into_queue(booking_id: UUID, available_online: bool):
    # 1) подключаемся
    conn = await connect_robust(rabbitmq_url)
    channel = await conn.channel()
    await channel.set_qos(prefetch_count=1)

    # 2) выбираем нужную очередь
    queue_name = PARS_QUEUE if available_online else CALL_QUEUE
    # гарантированно объявляем с тем же durable-флагом, что и потребитель
    await channel.declare_queue(queue_name, durable=True)

    # 3) публикуем
    body = json.dumps({"booking_id": str(booking_id)})
    await channel.default_exchange.publish(
        Message(body.encode(), content_type="application/json"),
        routing_key=queue_name,
    )
    await conn.close()


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

    try:
        # Проверка, существует ли место
        result = await db.execute(select(Place).where(Place.id == booking.place_id))
        place = result.scalars().first()
        if not place:
            raise HTTPException(status_code=404, detail="Place not found")

        # Создание новой брони
        db_booking = Booking(
            id=uuid.uuid4(),
            user_id=current_user.id,
            place_id=booking.place_id,
            booking_date=booking.booking_date,
            num_of_people=booking.num_of_people,
            special_requests=booking.special_requests,
        )

        db.add(db_booking)
        await db.commit()
        await db.refresh(db_booking)

        # Очередь
        await put_into_queue(db_booking.id, place.available_online)

        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Бронирование успешно создано"},
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# Pydantic модели для ответа
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
    confirmed: bool
    member: MemberResponse
    place: PlaceResponse

    class Config:
        json_encoders = {uuid.UUID: lambda x: str(x)}
        from_attributes = True


# GET все бронирования по member
@router.get("/bookings")
async def get_all_bookings(db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(Booking).options(
            selectinload(Booking.member),
            selectinload(Booking.place).options(
                selectinload(Place.metro_stations),
                selectinload(Place.cuisines),
            ),
        )

        result = await db.execute(stmt)
        bookings = result.scalars().all()

        upcoming_bookings = []
        past_bookings = []

        for booking in bookings:
            serialized = BookingResponse.from_orm(booking).dict()
            if booking.confirmed:
                past_bookings.append(serialized)
            else:
                upcoming_bookings.append(serialized)

        return {"upcoming_bookings": upcoming_bookings, "past_bookings": past_bookings}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
