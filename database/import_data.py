import sys
import os
import asyncio
import uuid
import json
import time
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


# ---------- LLM helper ----------------------------------------------------- #
def generate_llm_reply(prompt: list[dict]) -> str:
    """Запрос к Groq-LLM с отладкой ошибок."""
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
        content = response.json()["choices"][0]["message"]["content"].strip()
        time.sleep(0.5)  # пауза между запросами к LLM
        return content
    except requests.RequestException as e:
        logger.error(f"[ERROR] Request failed: {e}")
        raise RuntimeError(f"Ошибка при получении ответа от модели: {e}")
    except (KeyError, IndexError) as e:
        logger.error(f"[ERROR] Invalid response structure: {e}")
        raise RuntimeError(f"Ошибка обработки ответа от модели: {e}")


def normalize_place_name(full_name: str, address: str) -> str:
    """Получает короткое имя заведения через LLM."""
    prompt = [
        {
            "role": "user",
            "content": f"""

Ты — система нормализации названий заведений.

Название: "{full_name}"
Адрес: "{address}"


Верни только одно строковое значение в формате:
<Короткое название> (ул. <название улицы>)
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
    """
    Контекст даёт сессию без авто-commit.
    Rollback делается на ошибке, commit — вручную.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка в сессии БД: {e}")
            raise
        finally:
            await session.close()


# ---------- Импорт --------------------------------------------------------- #
BATCH_SIZE = 30  # сколько заведений фиксируем одним commit'ом


async def import_from_json(filename: str) -> None:
    logger.info(f"📂 Начат импорт из файла: {filename}")
    await create_tables()

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    added = 0
    skipped = 0

    async with get_async_session() as session:
        for place_data in data:
            # пропускаем дубликаты
            dup_q = select(Place).where(
                Place.full_name == place_data["full_name"],
                Place.address == place_data["address"],
            )
            if (await session.execute(dup_q)).scalar():
                skipped += 1
                logger.info(f"↩️ Пропущено дубликат: {place_data['full_name']}")
                continue

            # проверяем «главную» ссылку бронирования
            bl = place_data.get("booking_links", {})

            has_main = (
                bool(bl.get("main"))
                if isinstance(bl, dict)
                else any(link.get("type") == "main" for link in bl)
            )

            place = Place(
                id=uuid.uuid4(),
                full_name=normalize_place_name(
                    place_data["full_name"], place_data["address"]
                ),
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
                    + " ".join(place_data.get("close_metro", ""))
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

            session.add(place)  # place должен быть в сессии сразу

            # связи
            await process_relationships(session, place, place_data)

            added += 1

            # commit каждые BATCH_SIZE объектов
            if added % BATCH_SIZE == 0:
                await session.commit()
                logger.info(
                    f"🚀 Добавлен батч из {BATCH_SIZE} заведений (всего: {added})"
                )
                await asyncio.sleep(10)

        # финальный commit
        await session.commit()
        logger.info(f"✅ Импорт завершён: добавлено {added}, пропущено {skipped}")


async def process_relationships(session, place: Place, place_data: dict) -> None:
    """
    Создаёт и привязывает связанные объекты.
    Используем *синхронный* with session.no_autoflush, чтобы place успел попасть в сессию.
    """
    with session.no_autoflush:  # <-- FIX here
        # alternate names
        for name in place_data["alternate_name"]:
            alt_name = (
                await session.execute(
                    select(AlternateName).where(AlternateName.name == name)
                )
            ).scalar()
            if not alt_name:
                alt_name = AlternateName(id=uuid.uuid4(), name=name)
                session.add(alt_name)
            place.alternate_names.append(alt_name)

        # metro
        for metro in place_data["close_metro"]:
            metro_obj = (
                await session.execute(
                    select(MetroStation).where(MetroStation.name == metro)
                )
            ).scalar()
            if not metro_obj:
                metro_obj = MetroStation(id=uuid.uuid4(), name=metro)
                session.add(metro_obj)
            place.metro_stations.append(metro_obj)

        # cuisine
        for cuisine in place_data["main_cuisine"]:
            cuisine_obj = (
                await session.execute(select(Cuisine).where(Cuisine.name == cuisine))
            ).scalar()
            if not cuisine_obj:
                cuisine_obj = Cuisine(id=uuid.uuid4(), name=cuisine)
                session.add(cuisine_obj)
            place.cuisines.append(cuisine_obj)

        # features
        for feature in place_data["features"]:
            feature_obj = (
                await session.execute(select(Feature).where(Feature.name == feature))
            ).scalar()
            if not feature_obj:
                feature_obj = Feature(id=uuid.uuid4(), name=feature)
                session.add(feature_obj)
            place.features.append(feature_obj)

        # purposes
        for purpose in place_data["visit_purposes"]:
            purpose_obj = (
                await session.execute(
                    select(VisitPurpose).where(VisitPurpose.name == purpose)
                )
            ).scalar()
            if not purpose_obj:
                purpose_obj = VisitPurpose(id=uuid.uuid4(), name=purpose)
                session.add(purpose_obj)
            place.visit_purposes.append(purpose_obj)

        # opening hours
        for day, hours in place_data["opening_hours"].items():
            place.opening_hours.append(
                OpeningHour(id=uuid.uuid4(), day=day, hours=hours)
            )

        # photos
        for photo_type, urls in place_data["photos"].items():
            for url in urls:
                place.photos.append(Photo(id=uuid.uuid4(), type=photo_type, url=url))

        # menu links
        for link_type, url in place_data["menu_links"].items():
            place.menu_links.append(MenuLink(id=uuid.uuid4(), type=link_type, url=url))

        # booking links
        for link_type, url in place_data["booking_links"].items():
            place.booking_links.append(
                BookingLink(id=uuid.uuid4(), type=link_type, url=url)
            )

        # reviews
        for r in place_data["reviews"]:
            place.reviews.append(
                Review(
                    id=uuid.uuid4(),
                    author=r["author"],
                    date=r["date"],
                    rating=r["rating"],
                    text=r["text"],
                    source=r.get("source"),
                )
            )


# ---------- Запуск как скрипта -------------------------------------------- #
if __name__ == "__main__":
    asyncio.run(import_from_json("database/restaurants.json"))
