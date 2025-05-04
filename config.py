# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# FastAPI / Uvicorn
uvicorn_host = os.getenv("UVICORN_HOST")

# Postgres
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_host = os.getenv("POSTGRES_HOST")
postgres_port = os.getenv("PG_PORT")
postgres_db = os.getenv("POSTGRES_DB")

# Telegram
telegram_token = os.getenv("BOT_TOKEN")
telegram_login = os.getenv("TELEGRAM_LOGIN")

# JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET", "some-exmpl-key")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
REFRESH_TOKEN_EXPIRE_DAYS = 7

# RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
USERNAME_QUEUE = os.getenv("USERNAME_QUEUE")
PASSWORD_QUEUE = os.getenv("PASSWORD_QUEUE")
CALL_QUEUE = os.getenv("CALL_QUEUE")
PARS_QUEUE = os.getenv("PARS_QUEUE")

# Собираем URL для aio_pika
rabbitmq_url = (
    f"amqp://{USERNAME_QUEUE}:{PASSWORD_QUEUE}" f"@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
)

# booking states
booking_success_state = os.getenv("BOOKING_SUCCESS_STATE")
booking_failure_state = os.getenv("BOOKING_FAILURE_STATE")

# print(postgres_user)