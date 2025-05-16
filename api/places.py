from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, or_, func, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import (
    Place as PlaceModel,
    AlternateName,
    Cuisine as CuisineModel,
    MetroStation as MetroModel,
)
from api.utils.schemas import PlaceSchema
from api.utils.logger import logger

router = APIRouter()


def create_tsvector(*args):
    exp = args[0]
    for e in args[1:]:
        exp += " " + e
    return func.to_tsvector("russian", exp)


@router.get("/places", response_model=List[PlaceSchema])
async def get_places(
    name: Optional[str] = None,
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
    similarity_threshold: float = Query(0, ge=0.0, le=1.0),
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
        logger.info(f"🔎 Поиск по имени: '{name}'")

        processed_name = name.translate(
            str.maketrans(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "абцдефгхийклмнопкрстюввхузАБЦДЕФГХИЙКЛМНОПКРСТЮВВХУЗ",
            )
        ).lower()

        stmt_fts = stmt.where(
            text(
                "to_tsvector('russian', search_text) @@ plainto_tsquery('russian', :query)"
            )
        ).params(query=processed_name)

        result_fts = await db.execute(stmt_fts.limit(limit))
        places_fts = result_fts.scalars().all()
        logger.info(f"🔠 Найдено по FTS: {len(places_fts)}")

        if len(places_fts) < limit // 2:
            stmt_similar = stmt.where(
                func.similarity(PlaceModel.search_text, name) > similarity_threshold
            ).order_by(func.similarity(PlaceModel.search_text, name).desc())
            result_similar = await db.execute(stmt_similar.limit(limit))
            places_similar = result_similar.scalars().all()
            logger.info(f"🧩 Найдено по similarity: {len(places_similar)}")
            return places_fts + places_similar[: limit - len(places_fts)]

        return places_fts

    stmt = stmt.order_by(PlaceModel.full_name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    results = result.scalars().all()
    logger.info(f"📄 Всего заведений без фильтрации: {len(results)}")
    return results
