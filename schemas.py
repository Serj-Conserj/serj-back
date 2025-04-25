from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

class CuisineBase(BaseModel):
    name: str

class Cuisine(CuisineBase):
    id: UUID
    
    class Config:
        orm_mode = True

class MetroStationBase(BaseModel):
    name: str

class MetroStation(MetroStationBase):
    id: UUID
    
    class Config:
        orm_mode = True

class PlaceBase(BaseModel):
    name: str
    alternate_name: Optional[str] = None
    address: Optional[str] = None
    goo_rating: Optional[float] = None
    party_booking_name: Optional[str] = None
    booking_form: Optional[str] = None

class PlaceCreate(PlaceBase):
    pass

class Place(PlaceBase):
    id: UUID
    cuisines: List[Cuisine] = []
    metro_stations: List[MetroStation] = []
    
    class Config:
        orm_mode = True