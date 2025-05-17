import asyncio
from celery_app import celery_app
from database.import_data import import_from_json
from database.parser_for_new_db import parse_for_db
from api.utils.logger import logger


@celery_app.task
def parse_places_task():
    logger.info("🛠️  Starting parse...")
    parse_for_db()
    logger.info("✅ Parsing done")


@celery_app.task
def import_places_task(filename: str):
    logger.info(f"📥 Starting import from {filename}...")
    asyncio.run(import_from_json(filename))
    logger.info("✅ Import done")
