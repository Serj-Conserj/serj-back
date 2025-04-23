from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import selectinload
from datetime import datetime
from database.database import get_db, AsyncSession
from database.models import Booking, Place
from sqlalchemy import select
import uuid
import pika
from config import connect_queue, call_queue, pars_queue


def put_into_queue(booking_id, available_online):
    connection_params = connect_queue()
    connection = pika.BlockingConnection(connection_params)

    channel = connection.channel()
    message = f'{{"booking_id": "{booking_id}"}}'

    # Cheking while our app will call or register online
    if available_online:
        channel.queue_declare(queue=pars_queue)
        channel.basic_publish(exchange="", routing_key=pars_queue, body=message)
    else:
        channel.queue_declare(queue=call_queue)
        channel.basic_publish(exchange="", routing_key=call_queue, body=message)

    connection.close()


router = APIRouter()


class BookingCreate(BaseModel):
    num_of_people: int
    booking_date: datetime
    place_id: str
    user_id: str
    recording_date: datetime
    special_requests: Optional[str] = None
    confirmed: Optional[bool] = None


@router.post("/bookings")
async def create_booking(booking: BookingCreate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Place).where(Place.id == booking.place_id))
        place = result.scalars().first()

        if not place:
            raise HTTPException(status_code=404, detail="Place not found")

        db_booking = Booking(
            **booking.dict(),
            id=uuid.uuid4(),
        )

        db.add(db_booking)
        await db.commit()
        await db.refresh(db_booking)
        put_into_queue(db_booking.id, place.available_online)

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Бронирование успешно создано",
            },
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

class PlaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    available_online: bool

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
        json_encoders = {
            uuid.UUID: lambda x: str(x)
        }

# GET все бронирования по member
@router.get("/bookings")
async def get_all_bookings(db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(Booking).options(
            selectinload(Booking.member),
            selectinload(Booking.place)
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

        return {
            "upcoming_bookings": upcoming_bookings,
            "past_bookings": past_bookings
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
