from pydantic import BaseModel, Field, validator
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
    full_name: str = Field(..., description="Полное официальное название заведения")  # Изменено name -> full_name
    phone: Optional[str] = Field(None, example="+7 999 123-45-67")
    address: str = Field(..., example="ул. Примерная, 15")  # Сделано обязательным
    type: Optional[str] = Field(None, example="Ресторан")
    average_check: Optional[str] = Field(None, example="1500-2500 руб.")
    description: Optional[str] = Field(None, example="Прекрасный ресторан с авторской кухней")
    deposit_rules: Optional[str]
    coordinates_lat: Optional[float]
    coordinates_lon: Optional[float]
    source_url: Optional[str]
    source_domain: Optional[str]
    available_online: bool
    
    # Relationships with computed fields
    rating: Optional[float] = Field(None, ge=1, le=5, description="Средний рейтинг на основе отзывов")
    cuisines: List[str] = Field(..., example=["Итальянская", "Японская"])  # Только названия
    metro_stations: List[str] = Field(..., example=["Чистые пруды", "Красные ворота"])
    alternate_names: List[str] = Field(..., example=["Фарш Мясо", "Farsh na Myasnoy"])
    features: List[str] = Field(..., example=["Веранда", "Парковка"])
    visit_purposes: List[str] = Field(..., example=["Романтический ужин", "Бизнес-ланч"])
    
    # Остальные связи остаются как объекты
    opening_hours: List[OpeningHourSchema] = []
    photos: List[PhotoSchema] = []
    menu_links: List[MenuLinkSchema] = []
    booking_links: List[BookingLinkSchema] = []
    reviews: List[ReviewSchema] = []

    class Config:
        from_attributes = True

    # Валидаторы для преобразования отношений в списки названий
    @validator('cuisines', pre=True)
    def extract_cuisine_names(cls, v):
        return [item.name for item in v] if isinstance(v, list) else []

    @validator('metro_stations', pre=True)
    def extract_metro_names(cls, v):
        return [item.name for item in v] if isinstance(v, list) else []

    @validator('alternate_names', pre=True)
    def extract_alt_names(cls, v):
        return [item.name for item in v] if isinstance(v, list) else []

    @validator('features', pre=True)
    def extract_feature_names(cls, v):
        return [item.name for item in v] if isinstance(v, list) else []

    @validator('visit_purposes', pre=True)
    def extract_purpose_names(cls, v):
        return [item.name for item in v] if isinstance(v, list) else []

    @validator('rating', pre=True)
    def calculate_rating(cls, v, values):
        if 'reviews' in values and isinstance(values['reviews'], list):
            ratings = [r.rating for r in values['reviews'] if r.rating]
            return round(sum(ratings)/len(ratings), 1) if ratings else None
        return None
