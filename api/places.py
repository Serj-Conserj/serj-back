# api/routers/places.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, or_, func
from typing import List
import re

from database.database import get_db
from database.models import Place, AlternateName, Review
from api.utils.schemas import PlaceSchema

router = APIRouter()

def prepare_search_query(raw_query: str) -> str:
    """Очистка и подготовка поискового запроса"""
    cleaned = re.sub(r'\s+', ' ', raw_query.strip())  # Удаляем лишние пробелы
    return f"%{cleaned}%"

@router.get("/places", response_model=List[PlaceSchema])
async def search_places(
    search: str = Query(..., min_length=2, max_length=100, description="Поиск по названию, адресу и описанию"),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    # Подготавливаем поисковый запрос
    search_query = prepare_search_query(search)
    
    # Создаем базовый запрос
    stmt = (
        select(Place)
        .options(
            selectinload(Place.cuisines),
            selectinload(Place.metro_stations),
            selectinload(Place.alternate_names),
            selectinload(Place.reviews)
        )
        .outerjoin(AlternateName)
        .where(
            or_(
                Place.full_name.ilike(search_query),
                Place.address.ilike(search_query),
                Place.description.ilike(search_query),
                AlternateName.name.ilike(search_query),
                func.to_tsvector('russian', Place.full_name).match(
                    func.plainto_tsquery('russian', search.strip())
                )
            )
        )
        .distinct()
        .limit(limit)
    )

    # Выполняем запрос
    result = await db.execute(stmt)
    places = result.scalars().all()
    
    if not places:
        raise HTTPException(
            status_code=404,
            detail="Ничего не найдено. Попробуйте изменить поисковый запрос"
        )
    
    return places