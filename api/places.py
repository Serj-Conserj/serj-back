from fastapi import APIRouter, FastAPI, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from . import models, schemas, database
import uuid

app = FastAPI()
router = APIRouter()

@router.get("/places")
def get_places():
    return [
        {
            "id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
            "name": "Пельменная №1",
            "service_type": "Ресторан",
            "metro": [{"id": 1, "name": "Пушкинская"}],
            "cuisine": [{"id": 1, "name": "Русская"}]
        },
        {
            "id": uuid.uuid4(),
            "name": "Sushi Go",
            "service_type": "Кафе",
            "metro": [{"id": 2, "name": "Таганская"}],
            "cuisine": [{"id": 2, "name": "Японская"}]
        }
    ]
