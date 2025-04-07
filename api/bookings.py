from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database.database import get_db, AsyncSession
from database.models import Booking
import uuid

router = APIRouter()


class BookingCreate(BaseModel):
    num_of_people: int
    booking_date: datetime
    place_id: str
    user_id: str
    recording_date: datetime
    special_requests: Optional[str] = None
    confirmed: Optional[bool] = None


@router.post("/bookings/")
async def create_booking(booking: BookingCreate, db: AsyncSession = Depends(get_db)):
    try:

        db_booking = Booking(
            **booking.dict(),
            id=uuid.uuid4(),
        )

        try:
            db.add(db_booking)
            await db.commit()
            await db.refresh(db_booking)

        except Exception as e:
            print(e)

        return {
            "status": "success",
            "data": {
                "id": str(db_booking.id),
                "num_of_people": db_booking.num_of_people,
                "booking_date": db_booking.booking_date.isoformat(),
                "confirmed": db_booking.confirmed,
            },
            "message": "Booking created successfully",
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
