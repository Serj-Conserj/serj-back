from dotenv import load_dotenv
import os
import pika

load_dotenv()


uvicorn_host = os.getenv("UVICORN_HOST")
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_host = os.getenv("POSTGRES_HOST")
postgres_port = os.getenv("PG_PORT")
postgres_db = os.getenv("POSTGRES_DB")
telegram_token = os.getenv("BOT_TOKEN")
telegram_login = os.getenv("TELEGRAM_LOGIN")
JWT_SECRET_KEY = os.getenv("JWT_SECRET", "some-exmpl-key") 
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
REFRESH_TOKEN_EXPIRE_DAYS = 7

def connect_queue():

    connection_params = pika.ConnectionParameters(
        host=os.getenv("HOST_QUEUE"),
        port=os.getenv("PORT_QUEUE"),
        virtual_host="/",
        credentials=pika.PlainCredentials(
            username=os.getenv("USERNAME_QUEUE"),
            password=os.getenv("PASSWORD_QUEUE"),
        ),
    )
    return connection_params


call_queue = os.getenv("CALL_QUEUE")
pars_queue = os.getenv("PARS_QUEUE")
