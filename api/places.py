from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.database import get_db
from database.models import (
    Place as PlaceModel,
    Cuisine as CuisineModel,
    MetroStation as MetroModel,
)
from api.utils.schemas import PlaceSchema

router = APIRouter()


@router.get("/places", response_model=List[PlaceSchema])
async def get_places(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    cuisine: Optional[str] = None,
    metro: Optional[str] = None,
    expand: Optional[List[str]] = Query(None),
):
    stmt = select(PlaceModel)

    # ВСЕГДА грузим связи cuisines и metro_stations через selectinload
    stmt = stmt.options(
        selectinload(PlaceModel.cuisines), selectinload(PlaceModel.metro_stations)
    )

    # Фильтрация
    if min_rating is not None:
        stmt = stmt.where(PlaceModel.goo_rating >= min_rating)

    if cuisine:
        stmt = stmt.join(PlaceModel.cuisines).where(
            CuisineModel.name.ilike(f"%{cuisine}%")
        )

    if metro:
        stmt = stmt.join(PlaceModel.metro_stations).where(
            MetroModel.name.ilike(f"%{metro}%")
        )

    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    places = result.scalars().all()

    return places
