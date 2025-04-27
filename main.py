import os
import platform
import uvicorn
from fastapi import FastAPI

from database.database import engine, Base
from api.bookings import router as bookings_router
from api.places import router as places_router
from sqlalchemy import text
from api.login import router as login_router
from config import uvicorn_host
from database.models import *

app = FastAPI()


app.include_router(places_router, prefix="/api")
app.include_router(bookings_router, prefix="/api")
app.include_router(login_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Hello, World!"}


@app.on_event("startup")
async def startup():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Таблицы успешно созданы.")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise


if __name__ == "__main__":
    uvicorn.run(app, host=uvicorn_host, port=8000)