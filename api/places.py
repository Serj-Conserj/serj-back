# project/api/places.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import models, schemas, database

router = APIRouter()

# Схема ответа
class CuisineSchema(schemas.BaseModel):
    id: int
    name: str

class MetroSchema(schemas.BaseModel):
    id: int
    name: str

class PlaceResponse(schemas.BaseModel):
    id: int
    name: str
    alternate_name: str | None
    address: str | None
    goo_rating: float | None
    party_booking_name: str | None
    booking_form: str | None
    available_online: bool
    cuisines: List[CuisineSchema]
    metro_stations: List[MetroSchema]

    class Config:
        orm_mode = True

@router.get("/places", response_model=List[PlaceResponse])
def get_places(db: Session = Depends(database.get_db)):
    try:
        places = db.query(models.Place)\
            .options(
                joinedload(models.Place.cuisines),
                joinedload(models.Place.metro_stations)
            )\
            .all()
        return places
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))