from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, or_, func, exists
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

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
    name: Optional[str] = None,
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
        similarity_threshold = 0.2
        place_sim = func.similarity(PlaceModel.full_name, name)
        place_condition = place_sim >= similarity_threshold
        
        # Переносим создание subquery ВНУТРЬ условия if name
        subquery = exists().where(
            place_alternate_names.c.place_id == PlaceModel.id,
            place_alternate_names.c.alternate_name_id == AlternateName.id,
            func.similarity(AlternateName.name, name) >= similarity_threshold
        )
        
        stmt = stmt.where(or_(place_condition, subquery))
        stmt = stmt.order_by(place_sim.desc())

    result = await db.execute(stmt)
    places = result.scalars().all()
    return places