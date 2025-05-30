from celery import Celery
from celery.schedules import crontab
import os

celery_app = Celery(
    "tasks",
    broker=f"amqp://{os.getenv('USERNAME_QUEUE')}:{os.getenv('PASSWORD_QUEUE')}@rabbitmq:5672//",
    backend=None,
    include=["tasks"],
)

celery_app.conf.timezone = "Europe/Moscow"
celery_app.conf.enable_utc = False

celery_app.conf.beat_schedule = {
    "parse-every-monday-4am": {
        "task": "tasks.parse_places_task",
        "schedule": crontab(hour=13, minute=17, day_of_week=6),
    },
    "import-every-tuesday-4am": {
        "task": "tasks.import_places_task",
        "schedule": crontab(hour=5, minute=0, day_of_week=2),
        "args": ("database/restaurants.json",),
    },
}
