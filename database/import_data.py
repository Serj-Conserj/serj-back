import sys
import os
import asyncio
import uuid
import json
from pathlib import Path
from contextlib import asynccontextmanager
from sqlalchemy import select

from database.models import (
    Place,
    AlternateName,
    MetroStation,
    Cuisine,
    Feature,
    VisitPurpose,
    OpeningHour,
    Photo,
    MenuLink,
    BookingLink,
    Review,
)
from database.database import engine, Base, AsyncSessionLocal


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_async_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def import_from_json(filename: str):
    await create_tables()

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    added = 0
    skipped = 0

    async with get_async_session() as session:
        for place_data in data:
            # Проверка: есть ли уже такая запись по full_name + address
            existing_place_result = await session.execute(
                select(Place).where(
                    Place.full_name == place_data["full_name"],
                    Place.address == place_data["address"],
                )
            )
            bl = place_data.get("booking_links", {})
            if isinstance(bl, dict):
                has_main = bool(bl.get("main"))
            else:
                has_main = any(item.get("type") == "main" for item in bl)
            print(f"has_main: {has_main}")
            if existing_place_result.scalar():
                skipped += 1
                continue
            
            place = Place(
                id=uuid.uuid4(),
                full_name=place_data["full_name"],
                phone=place_data["phone"],
                address=place_data["address"],
                type=place_data["type"],
                average_check=str(place_data.get("average_check")),
                description=place_data["description"],
                deposit_rules=place_data.get("deposit_rules"),
                coordinates_lat=place_data["coordinates"]["lat"],
                coordinates_lon=place_data["coordinates"]["lon"],
                source_url=place_data["source"]["url"],
                source_domain=place_data["source"]["domain"],
                available_online=has_main,
            )

            await process_relationships(session, place, place_data)
            session.add(place)
            added += 1

        print(f"✅ Импорт завершён: добавлено {added}, пропущено {skipped}")


async def process_relationships(session, place, place_data):
    # Альтернативные названия
    for name in place_data["alternate_name"]:
        result = await session.execute(
            select(AlternateName).where(AlternateName.name == name)
        )
        alt_name = result.scalar()
        if not alt_name:
            alt_name = AlternateName(id=uuid.uuid4(), name=name)
            session.add(alt_name)
        place.alternate_names.append(alt_name)

    # Метро
    for metro in place_data["close_metro"]:
        result = await session.execute(
            select(MetroStation).where(MetroStation.name == metro)
        )
        metro_obj = result.scalar()
        if not metro_obj:
            metro_obj = MetroStation(id=uuid.uuid4(), name=metro)
            session.add(metro_obj)
        place.metro_stations.append(metro_obj)

    # Кухни
    for cuisine in place_data["main_cuisine"]:
        result = await session.execute(select(Cuisine).where(Cuisine.name == cuisine))
        cuisine_obj = result.scalar()
        if not cuisine_obj:
            cuisine_obj = Cuisine(id=uuid.uuid4(), name=cuisine)
            session.add(cuisine_obj)
        place.cuisines.append(cuisine_obj)

    # Особенности
    for feature in place_data["features"]:
        result = await session.execute(select(Feature).where(Feature.name == feature))
        feature_obj = result.scalar()
        if not feature_obj:
            feature_obj = Feature(id=uuid.uuid4(), name=feature)
            session.add(feature_obj)
        place.features.append(feature_obj)

    # Цели посещения
    for purpose in place_data["visit_purposes"]:
        result = await session.execute(
            select(VisitPurpose).where(VisitPurpose.name == purpose)
        )
        purpose_obj = result.scalar()
        if not purpose_obj:
            purpose_obj = VisitPurpose(id=uuid.uuid4(), name=purpose)
            session.add(purpose_obj)
        place.visit_purposes.append(purpose_obj)

    # Часы работы
    for day, hours in place_data["opening_hours"].items():
        place.opening_hours.append(OpeningHour(id=uuid.uuid4(), day=day, hours=hours))

    # Фотографии
    for photo_type, urls in place_data["photos"].items():
        for url in urls:
            place.photos.append(Photo(id=uuid.uuid4(), type=photo_type, url=url))

    # Ссылки на меню
    for link_type, url in place_data["menu_links"].items():
        place.menu_links.append(MenuLink(id=uuid.uuid4(), type=link_type, url=url))

    # Ссылки на бронирование
    for link_type, url in place_data["booking_links"].items():
        place.booking_links.append(
            BookingLink(id=uuid.uuid4(), type=link_type, url=url)
        )

    # Отзывы
    for review_data in place_data["reviews"]:
        place.reviews.append(
            Review(
                id=uuid.uuid4(),
                author=review_data["author"],
                date=review_data["date"],
                rating=review_data["rating"],
                text=review_data["text"],
                source=review_data.get("source"),
            )
        )


if __name__ == "__main__":
    asyncio.run(import_from_json("database/restaurants.json"))
