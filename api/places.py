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
    similarity_threshold: float = Query(0.3, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает список заведений.

    * Если передан `name`, сначала ищем полным-текстовым поиском (FTS),
      а при недостатке результатов – догружаем по trigram-similarity.
    * Дубликаты по `id` всегда убираются.
    """
    stmt_base = select(PlaceModel).options(
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

    # ------------------------------------------------------------------
    # Поиск по имени
    # ------------------------------------------------------------------
    if name:
        logger.info(f"🔎 Поиск по имени: '{name}'")

        # Приводим к кириллице (simple latin->cyr mapping), затем в lower-case
        processed_name = name.translate(
            str.maketrans(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "абцдефгхийклмнопкрстюввхузАБЦДЕФГХИЙКЛМНОПКРСТЮВВХУЗ",
            )
        ).lower()

        # ---------- FTS ----------
        stmt_fts = stmt_base.where(
            text(
                "to_tsvector('russian', search_text) "
                "@@ plainto_tsquery('russian', :query)"
            )
        ).params(query=processed_name)

        fts_res = await db.execute(stmt_fts.limit(limit))
        places_fts = fts_res.scalars().all()
        logger.info(f"🔠 Найдено по FTS: {len(places_fts)}")

        # ---------- similarity ----------
        if len(places_fts) < limit // 2:
            ids_fts = [p.id for p in places_fts]
            stmt_sim = (
                stmt_base.where(
                    func.similarity(PlaceModel.search_text, name)
                    > similarity_threshold,
                    PlaceModel.id.notin_(ids_fts),  # убираем дубли на уровне SQL
                )
                .order_by(func.similarity(PlaceModel.search_text, name).desc())
                .limit(limit)
            )
            sim_res = await db.execute(stmt_sim)
            places_similar = sim_res.scalars().all()
            logger.info(f"🧩 Найдено по similarity: {len(places_similar)}")

            combined = places_fts + places_similar
        else:
            combined = places_fts

        # ---------- финальная дедупликация ----------
        unique: list[PlaceModel] = []
        seen: set[UUID] = set()
        for place in combined:
            if place.id not in seen:
                seen.add(place.id)
                unique.append(place)

        return unique[:limit]

    # ------------------------------------------------------------------
    # Без имени: постраничная выдача
    # ------------------------------------------------------------------
    stmt_default = stmt_base.order_by(PlaceModel.full_name).offset(offset).limit(limit)
    result = await db.execute(stmt_default)
    rows = result.scalars().all()
    logger.info(f"📄 Всего заведений без фильтрации: {len(rows)}")
    return rows
