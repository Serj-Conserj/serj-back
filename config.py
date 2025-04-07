from dotenv import load_dotenv
import os

load_dotenv()


uvicorn_host = os.getenv("UVICORN_HOST")
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_host = os.getenv("POSTGRES_HOST")
postgres_port = os.getenv("PG_PORT")
postgres_db = os.getenv("POSTGRES_DB")
telegram_token = os.getenv("TELEGRAM_TOKEN")
telegram_login = os.getenv("TELEGRAM_LOGIN")
jwt_secret = os.getenv("JWT_SECRET")
