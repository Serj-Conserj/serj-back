# 🍽️ ConSerj Backend (`serj-back`)

> **An AI‑powered service that turns restaurant booking from a tedious phone call into a single‑click experience.**

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-async%20REST-green?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![Celery](https://img.shields.io/badge/Celery-distributed tasks-orange?logo=celery)
![Docker](https://img.shields.io/badge/Docker-containerised-black?logo=docker)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)

---

## 🚀 Key Features

| 💡 Feature                      | Description                                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------------------------- |
| 📝 **API**                      | High‑performance REST endpoints built with FastAPI for bookings, authentication, and data import. |
| 🔑 **Login via Telegram**       | Password‑less auth: validate `initData`, issue JWTs, instant WebApp sign‑in.                      |
| ⚙️ **Celery + RabbitMQ**        | Asynchronous queues for menu parsing, auto‑dialer, and scheduled restaurant imports.              |
| 🗄️ **PostgreSQL + SQLAlchemy** | Clean data models and Alembic migrations.                                                         |
| 🩺 **Health‑checks / Metrics**  | Ready for Prometheus; logs are unified and sent to stdout.                                        |
| 🐳 **Docker‑first**             | One‑command deployment, CI/CD‑ready (Drone).                                                      |

---

## 🗂️ Repository Structure

```text
serj-back
├── api/                     # 🔌  FastAPI routes
├── database/                # 🗄️  SQLAlchemy models & helpers
│   ├── database.py          # → async‑session factory
│   ├── models.py            # → ORM schemas 
│   ├── import_data.py       # → initial import from restaurants.json
│   └── parser_for_new_db.py # → LeClick / Banket parser
├── tasks.py                 # ⚙️  Celery task entry point
├── celery_app.py            # ⚙️  Celery Workers & Beat config
├── celerybeat-schedule      # 🕒  auto‑generated beat schedule
├── config.py                # 🔧  Pydantic settings (env vars)
├── main.py                  # 🚀  Uvicorn entry point
├── Dockerfile               # 🐳  Application image
├── drone.yaml               # 🤖  CI pipeline (Drone)
├── requirements.txt         # 📦  Dependencies
└── README.md                # 📚  You are here
```

> **Bolded** folders below are the ones you will touch most often.

| Folder          | Purpose                                         |
| --------------- | ----------------------------------------------- |
| **`api/`**      | Endpoints and Pydantic request/response schemas |
| **`database/`** | Data models, importers, and parsers             |
| **`tasks.py`**  | Macro wrappers around Celery async tasks        |

---

## 📋 Environment Variables

### Backend (`uvicorn`)

| Variable       | Default                                       | Purpose                                    |
| -------------- | --------------------------------------------- | ------------------------------------------ |
| `UVICORN_HOST` | `0.0.0.0`                                     | Network interface on which FastAPI listens |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@db:5432/serj` | PostgreSQL connection string               |
| `RABBIT_URL`   | `amqp://guest:guest@rabbit:5672/`             | Celery broker URL                          |
| `BOT_TOKEN`    | —                                             | Telegram bot token                         |
| `SECRET_KEY`   | —                                             | JWT signing key                            |
| `GROQ_TOKEN`   | —                                             | GroqCloud API token (LLM inference)        |

### Consumer (Celery Workers)

| Variable                | Default         | Purpose                               |
| ----------------------- | --------------- | ------------------------------------- |
| `HOST_QUEUE`            | `92.53.107.207` | RabbitMQ host                         |
| `PORT_QUEUE`            | `5672`          | RabbitMQ port                         |
| `USERNAME_QUEUE`        | `admin`         | RabbitMQ username                     |
| `PASSWORD_QUEUE`        | `132465`        | RabbitMQ password                     |
| `CALL_QUEUE`            | `call_queue`    | Queue for call‑processing tasks       |
| `PARS_QUEUE`            | `pars_queue`    | Queue for parsing tasks               |
| `BOOKING_SUCCESS_STATE` | `booked`        | Status label for a successful booking |
| `BOOKING_FAILURE_STATE` | `failed`        | Status label for a failed booking     |

> **Tip:** the full list (with defaults) lives in `config.py`, powered by Pydantic `BaseSettings`.

\----------|---------|---------|
\| `DATABASE_URL` | `postgresql+asyncpg://user:pass@db:5432/serj` | Postgres connection string |
\| `RABBIT_URL` | `amqp://guest:guest@rabbit:5672/` | Celery broker |
\| `BOT_TOKEN` | — | Telegram bot token |
\| `SECRET_KEY` | — | JWT signature key |

See `config.py` (Pydantic `BaseSettings`) for the full list.

---

## 📑 API at a Glance

| Method | Path             | Description               |
| ------ | ---------------- | ------------------------- |
| `POST` | `/api/bookings`  | Create a booking          |
| `GET`  | `/api/bookings`  | List user bookings        |
| `POST` | `/auth/telegram` | Exchange `initData` → JWT |
| `POST` | `/auth/refresh`  | Refresh access token      |

The full interactive spec is available at `/docs` (Swagger UI).

