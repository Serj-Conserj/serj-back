from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


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
