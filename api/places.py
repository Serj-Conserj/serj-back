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
    name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    stmt = select(PlaceModel).options(
        selectinload(PlaceModel.cuisines),
        selectinload(PlaceModel.metro_stations),
    )

    if name:
        stmt = stmt.where(PlaceModel.name.ilike(f"%{name}%"))

    result = await db.execute(stmt)
    places = result.scalars().all()

    return places
