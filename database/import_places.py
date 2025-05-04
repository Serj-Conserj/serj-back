import sys
import os
import asyncio
import uuid
import json
from pathlib import Path
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

# Добавляем корень проекта в пути поиска модулей
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models import Base, Place, AlternateName, MetroStation, Cuisine, Feature, VisitPurpose, \
    OpeningHour, Photo, MenuLink, BookingLink, Review
from app_config import (
    postgres_user,
    postgres_password,
    postgres_host,
    postgres_port,
    postgres_db,
)

async def get_async_engine():
    database_url = (
        f"postgresql+asyncpg://{postgres_user}:{postgres_password}@"
        f"{postgres_host}:{postgres_port}/{postgres_db}"
    )
    return create_async_engine(database_url, echo=False)

async def create_tables(engine, clear_existing=False):
    async with engine.begin() as conn:
        if clear_existing:
            # Добавляем CASCADE для удаления зависимых объектов
            await conn.run_sync(
                lambda sync_conn: Base.metadata.drop_all(
                    sync_conn, 
                    tables=None, 
                    cascade=True,  # Добавляем каскадное удаление
                    checkfirst=False
                )
            )
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def get_async_session():
    engine = await get_async_engine()
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def import_from_json(filename: str, clear_existing=True):
    engine = await get_async_engine()
    await create_tables(engine, clear_existing=clear_existing)
    
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    async with get_async_session() as session:
        for place_data in data:
            place = Place(
                id=uuid.uuid4(),
                full_name=place_data['full_name'],
                phone=place_data['phone'],
                address=place_data['address'],
                type=place_data['type'],
                average_check=place_data.get('average_check'),
                description=place_data['description'],
                deposit_rules=place_data.get('deposit_rules'),
                coordinates_lat=place_data['coordinates']['lat'],
                coordinates_lon=place_data['coordinates']['lon'],
                source_url=place_data['source']['url'],
                source_domain=place_data['source']['domain']
            )

            # Обработка связей
            await process_relationships(session, place, place_data)
            
            session.add(place)
            await session.commit()

async def process_relationships(session, place, place_data):
    # Альтернативные названия
    for name in place_data['alternate_name']:
        alt_name = await session.run_sync(lambda s: s.query(AlternateName).filter_by(name=name).first())
        if not alt_name:
            alt_name = AlternateName(id=uuid.uuid4(), name=name)
            session.add(alt_name)
        place.alternate_names.append(alt_name)

    # Метро
    for metro in place_data['close_metro']:
        metro_obj = await session.run_sync(lambda s: s.query(MetroStation).filter_by(name=metro).first())
        if not metro_obj:
            metro_obj = MetroStation(id=uuid.uuid4(), name=metro)
            session.add(metro_obj)
        place.metro_stations.append(metro_obj)

    # Кухни
    for cuisine in place_data['main_cuisine']:
        cuisine_obj = await session.run_sync(lambda s: s.query(Cuisine).filter_by(name=cuisine).first())
        if not cuisine_obj:
            cuisine_obj = Cuisine(id=uuid.uuid4(), name=cuisine)
            session.add(cuisine_obj)
        place.cuisines.append(cuisine_obj)

    # Особенности
    for feature in place_data['features']:
        feature_obj = await session.run_sync(lambda s: s.query(Feature).filter_by(name=feature).first())
        if not feature_obj:
            feature_obj = Feature(id=uuid.uuid4(), name=feature)
            session.add(feature_obj)
        place.features.append(feature_obj)

    # Цели посещения
    for purpose in place_data['visit_purposes']:
        purpose_obj = await session.run_sync(lambda s: s.query(VisitPurpose).filter_by(name=purpose).first())
        if not purpose_obj:
            purpose_obj = VisitPurpose(id=uuid.uuid4(), name=purpose)
            session.add(purpose_obj)
        place.visit_purposes.append(purpose_obj)

    # Часы работы
    for day, hours in place_data['opening_hours'].items():
        place.opening_hours.append(OpeningHour(
            id=uuid.uuid4(),
            day=day,
            hours=hours
        ))

    # Фотографии
    for photo_type, urls in place_data['photos'].items():
        for url in urls:
            place.photos.append(Photo(
                id=uuid.uuid4(),
                type=photo_type,
                url=url
            ))

    # Ссылки на меню
    for link_type, url in place_data['menu_links'].items():
        place.menu_links.append(MenuLink(
            id=uuid.uuid4(),
            type=link_type,
            url=url
        ))

    # Ссылки на бронирование
    for link_type, url in place_data['booking_links'].items():
        place.booking_links.append(BookingLink(
            id=uuid.uuid4(),
            type=link_type,
            url=url
        ))

    # Отзывы
    for review_data in place_data['reviews']:
        place.reviews.append(Review(
            id=uuid.uuid4(),
            author=review_data['author'],
            date=review_data['date'],
            rating=review_data['rating'],
            text=review_data['text'],
            source=review_data.get('source')
        ))

if __name__ == '__main__':
    import asyncio
    asyncio.run(import_from_json('restaurants.json', clear_existing=False))
