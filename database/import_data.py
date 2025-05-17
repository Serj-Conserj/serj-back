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
from api.utils.logger import logger
import requests


def generate_llm_reply(prompt: list[dict]) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_TOKEN')}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "llama3-70b-8192",
        "messages": prompt,
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 1,
        "stream": False,
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    except requests.RequestException as e:
        logger.error(f"[ERROR] Request failed: {e}")
        raise RuntimeError(f"Ошибка при получении ответа от модели: {e}")

    except (KeyError, IndexError) as e:
        logger.error(f"[ERROR] Invalid response structure: {e}")
        raise RuntimeError(f"Ошибка обработки ответа от модели: {e}")


def normalize_place_name(full_name: str, address: str) -> str:
    prompt = [
        {
            "role": "user",
            "content": f"""
                Ты — система нормализации названий заведений.

                Название: "{full_name}"
                Адрес: "{address}"

                Верни только одно строковое значение в формате:
                <Короткое название> (ул. <название улицы>)

                ❗️ Удали слова вроде "ресторан", "кафе", "бар", "пиццерия", спецсимволы и хештеги.  
                ❗️ Название должно быть кратким.  
                ❗️ Из адреса нужно выделить название улицы и подставить в скобки.  
                ❗️ Никаких пояснений, только результат.

                Пример:
                Название: "Ресторан #Фарш на мясницкой"
                Адрес: "Мясницкая улица д. 8"
                Ответ: Фарш (ул. Мясницкая)
                """.strip(),
        }
    ]

    return generate_llm_reply(prompt)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("📦 Таблицы успешно созданы.")


@asynccontextmanager
async def get_async_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка в сессии БД: {e}")
            raise
        finally:
            await session.close()


async def import_from_json(filename: str):
    logger.info(f"📂 Начат импорт из файла: {filename}")
    await create_tables()

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    added = 0
    skipped = 0

    async with get_async_session() as session:
        for place_data in data:
            existing_place_result = await session.execute(
                select(Place).where(
                    Place.full_name == place_data["full_name"],
                    Place.address == place_data["address"],
                )
            )
            if existing_place_result.scalar():
                skipped += 1
                logger.debug(f"↩️ Пропущено дубликат: {place_data['full_name']}")
                continue

            bl = place_data.get("booking_links", {})
            if isinstance(bl, dict):
                has_main = bool(bl.get("main"))
            else:
                has_main = any(item.get("type") == "main" for item in bl)
            normalized_name = normalize_place_name(
                full_name=place_data["full_name"], address=place_data["address"]
            )
            place = Place(
                id=uuid.uuid4(),
                full_name=normalized_name,
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
                search_text=(
                    place_data["full_name"]
                    + " "
                    + place_data["address"]
                    + " ".join(name for name in place_data.get("close_metro", ""))
                )
                .translate(
                    str.maketrans(
                        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
                        "абцдефгхийклмнопкрстюввхузАБЦДЕФГХИЙКЛМНОПКРСТЮВВХУЗ",
                    )
                )
                .lower(),
                available_online=has_main,
            )

            await process_relationships(session, place, place_data)

            session.add(place)
            added += 1
            logger.debug(f"✅ Добавлено заведение: {place.full_name}")

        logger.info(f"🏁 Импорт завершён: добавлено {added}, пропущено {skipped}")


async def process_relationships(session, place, place_data):
    for name in place_data["alternate_name"]:
        result = await session.execute(
            select(AlternateName).where(AlternateName.name == name)
        )
        alt_name = result.scalar()
        if not alt_name:
            alt_name = AlternateName(id=uuid.uuid4(), name=name)
            session.add(alt_name)
        place.alternate_names.append(alt_name)

    for metro in place_data["close_metro"]:
        result = await session.execute(
            select(MetroStation).where(MetroStation.name == metro)
        )
        metro_obj = result.scalar()
        if not metro_obj:
            metro_obj = MetroStation(id=uuid.uuid4(), name=metro)
            session.add(metro_obj)
        place.metro_stations.append(metro_obj)

    for cuisine in place_data["main_cuisine"]:
        result = await session.execute(select(Cuisine).where(Cuisine.name == cuisine))
        cuisine_obj = result.scalar()
        if not cuisine_obj:
            cuisine_obj = Cuisine(id=uuid.uuid4(), name=cuisine)
            session.add(cuisine_obj)
        place.cuisines.append(cuisine_obj)

    for feature in place_data["features"]:
        result = await session.execute(select(Feature).where(Feature.name == feature))
        feature_obj = result.scalar()
        if not feature_obj:
            feature_obj = Feature(id=uuid.uuid4(), name=feature)
            session.add(feature_obj)
        place.features.append(feature_obj)

    for purpose in place_data["visit_purposes"]:
        result = await session.execute(
            select(VisitPurpose).where(VisitPurpose.name == purpose)
        )
        purpose_obj = result.scalar()
        if not purpose_obj:
            purpose_obj = VisitPurpose(id=uuid.uuid4(), name=purpose)
            session.add(purpose_obj)
        place.visit_purposes.append(purpose_obj)

    for day, hours in place_data["opening_hours"].items():
        place.opening_hours.append(OpeningHour(id=uuid.uuid4(), day=day, hours=hours))

    for photo_type, urls in place_data["photos"].items():
        for url in urls:
            place.photos.append(Photo(id=uuid.uuid4(), type=photo_type, url=url))

    for link_type, url in place_data["menu_links"].items():
        place.menu_links.append(MenuLink(id=uuid.uuid4(), type=link_type, url=url))

    for link_type, url in place_data["booking_links"].items():
        place.booking_links.append(
            BookingLink(id=uuid.uuid4(), type=link_type, url=url)
        )

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
