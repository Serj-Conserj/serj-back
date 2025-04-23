from fastapi import APIRouter
from typing import List

router = APIRouter()

@router.get("/places")
def get_places():
    return [
        {
            "id": 1,
            "name": "Пельменная №1",
            "service_type": "Ресторан",
            "metro": [{"id": 1, "name": "Пушкинская"}],
            "cuisine": [{"id": 1, "name": "Русская"}]
        },
        {
            "id": 2,
            "name": "Sushi Go",
            "service_type": "Кафе",
            "metro": [{"id": 2, "name": "Таганская"}],
            "cuisine": [{"id": 2, "name": "Японская"}]
        }
    ]
