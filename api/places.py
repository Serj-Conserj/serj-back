from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional


from database.database import get_db
from database.models import (
    Place as PlaceModel,
    AlternateName,
    Cuisine as CuisineModel,
    MetroStation as MetroModel,
)
from api.utils.schemas import PlaceSchema

router = APIRouter()

TRANSLIT_MAP = {
    'a': 'а', 'A': 'А',
    'B': 'В', 'c': 'с', 'C': 'С',
    'e': 'е', 'E': 'Е',
    'o': 'о', 'O': 'О',
    'p': 'р', 'P': 'Р',
    'H': 'Н', 'K': 'К',
    'x': 'х', 'X': 'Х',
    'y': 'у', 'Y': 'У',
    'M': 'М', 'T': 'Т',
    'r': 'р', 'R': 'Р',
    's': 'с', 'S': 'С',
    'F': 'Ф', 'W': 'Ш'  # Пример для "FARШ"
}

def normalize_search_term(term: str) -> str:
    """Транслитерируем латиницу в кириллицу и очищаем от спецсимволов"""
    # Заменяем символы согласно словарю
    transliterated = ''.join([TRANSLIT_MAP.get(c, c) for c in term])
    # Удаляем оставшиеся спецсимволы
    cleaned = transliterated.translate(str.maketrans('', '', '!@#$%^&*()_+<>?.,;:-'))
    return cleaned.strip().lower()

@router.get("/places", response_model=List[PlaceSchema])
async def get_places(
    name: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PlaceModel).options(
        selectinload(PlaceModel.cuisines),
        selectinload(PlaceModel.metro_stations),
        selectinload(PlaceModel.alternate_names),
        selectinload(PlaceModel.features),
        selectinload(PlaceModel.visit_purposes),
        selectinload(PlaceModel.opening_hours),
        selectinload(PlaceModel.photos),
        selectinload(PlaceModel.menu_links),
        selectinload(PlaceModel.booking_links),
        selectinload(PlaceModel.reviews),
    )

    if name:
        normalized_name = normalize_search_term(name)
        
        # Создаем выражения для нормализации названий в базе
        base_normalization = func.regexp_replace(
            func.lower(PlaceModel.full_name),
            '[^\\w\\sа-яА-Я]', 
            '', 
            'g'
        )
        
        # Добавляем замену латинских символов через SQL-функцию
        normalized_full_name = func.translate(
            base_normalization,
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'абсдефгхийклмнопрстуввхызАБСДЕФГХИЙКЛМНОПРСТУВВХЫЗ'
        )

        # Аналогично для альтернативных названий
        alt_normalization = func.regexp_replace(
            func.lower(AlternateName.name),
            '[^\\w\\sа-яА-Я]', 
            '', 
            'g'
        )
        normalized_alt_name = func.translate(
            alt_normalization,
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'абсдефгхийклмнопрстуввхызАБСДЕФГХИЙКЛМНОПРСТУВВХЫЗ'
        )

        stmt = stmt.outerjoin(PlaceModel.alternate_names)
        stmt = stmt.where(
            or_(
                normalized_full_name.ilike(f"%{normalized_name}%"),
                normalized_alt_name.ilike(f"%{normalized_name}%")
            )
        )

    # Пагинация и сортировка
    stmt = stmt.distinct().order_by(PlaceModel.full_name).offset(offset).limit(limit)

    result = await db.execute(stmt)
    places = result.scalars().all()
    return places