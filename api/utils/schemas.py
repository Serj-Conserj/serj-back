from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


# ---------- Login ----------
class TelegramAuth(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: Optional[int] = None
    hash: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh: str


# ---------- Places ----------
class CuisineBaseSchema(BaseModel):
    name: str


class CuisineSchema(CuisineBaseSchema):
    id: UUID

    class Config:
        from_attributes = True


class MetroStationBaseSchema(BaseModel):
    name: str


class MetroStationSchema(MetroStationBaseSchema):
    id: UUID

    class Config:
        from_attributes = True


class PlaceBaseSchema(BaseModel):
    name: str
    alternate_name: Optional[str] = None
    address: Optional[str] = None
    goo_rating: Optional[float] = None
    party_booking_name: Optional[str] = None
    booking_form: Optional[str] = None


class PlaceSchema(PlaceBaseSchema):
    id: UUID
    cuisines: List[CuisineSchema] = []
    metro_stations: List[MetroStationSchema] = []

    class Config:
        from_attributes = True
