from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, or_, func, exists
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import re

from database.database import get_db
from database.models import (
    Place as PlaceModel,
    Cuisine as CuisineModel,
    MetroStation as MetroModel,
    place_alternate_names,
    AlternateName
)
from api.utils.schemas import PlaceSchema

router = APIRouter()

# Полный исправленный эндпоинт
@router.get("/places", response_model=List[PlaceSchema])
async def get_places(
    query: Optional[str] = None,
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

    clean_query = re.sub(r'[^a-zа-яё0-9]', '', query.lower())

    # Основное условие поиска
    stmt = select(PlaceModel).options(
        selectinload(PlaceModel.alternate_names)
    ).where(
        or_(
            # Поиск по основному названию
            func.regexp_replace(func.lower(PlaceModel.full_name), '[^a-zа-яё0-9]', '', 'g') == clean_query,
            
            # Поиск по альтернативным названиям
            exists().where(
                PlaceModel.id == place_alternate_names.c.place_id,
                AlternateName.id == place_alternate_names.c.alternate_name_id,
                func.regexp_replace(func.lower(AlternateName.name), '[^a-zа-яё0-9]', '', 'g') == clean_query
            )
        )
    )

    result = await db.execute(stmt)
    return result.scalars().all()