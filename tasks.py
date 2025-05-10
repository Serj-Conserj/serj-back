import asyncio
from celery_app import celery_app
from database.import_data import import_from_json
from database.parser_for_new_db import parse_for_db


@celery_app.task
def parse_places_task():
    print("Starting parse...")
    asyncio.run(parse_for_db())
    print("Parsing done")


@celery_app.task
def import_places_task(filename: str):
    print("Starting import...")
    asyncio.run(import_from_json(filename))
    print("Import done")
