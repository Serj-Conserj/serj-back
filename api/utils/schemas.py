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
class AlternateNameSchema(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class MetroStationSchema(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class CuisineSchema(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class FeatureSchema(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class VisitPurposeSchema(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class OpeningHourSchema(BaseModel):
    id: UUID
    day: str
    hours: str

    class Config:
        from_attributes = True


class PhotoSchema(BaseModel):
    id: UUID
    type: str
    url: str

    class Config:
        from_attributes = True


class MenuLinkSchema(BaseModel):
    id: UUID
    type: str
    url: str

    class Config:
        from_attributes = True


class BookingLinkSchema(BaseModel):
    id: UUID
    type: str
    url: str

    class Config:
        from_attributes = True


class ReviewSchema(BaseModel):
    id: UUID
    author: str
    date: str
    rating: int
    text: str
    source: Optional[str]

    class Config:
        from_attributes = True


class PlaceSchema(BaseModel):
    id: UUID
    name: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    type: Optional[str]
    average_check: Optional[str]
    description: Optional[str]
    deposit_rules: Optional[str]
    coordinates_lat: Optional[float]
    coordinates_lon: Optional[float]
    source_url: Optional[str]
    source_domain: Optional[str]
    available_online: bool

    alternate_names: List[AlternateNameSchema] = []
    metro_stations: List[MetroStationSchema] = []
    cuisines: List[CuisineSchema] = []
    features: List[FeatureSchema] = []
    visit_purposes: List[VisitPurposeSchema] = []
    opening_hours: List[OpeningHourSchema] = []
    photos: List[PhotoSchema] = []
    menu_links: List[MenuLinkSchema] = []
    booking_links: List[BookingLinkSchema] = []
    reviews: List[ReviewSchema] = []

    class Config:
        from_attributes = True
