# 🍽️ ConSerj Backend (`serj-back`)

> **An AI‑powered service that turns restaurant booking from a tedious phone call into a single‑click experience.**

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-async%20REST-green?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![Celery](https://img.shields.io/badge/Celery-distributed%20tasks-orange?logo=celery)
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
| 🐳 **Docker‑first**             | One‑command deployment, CI/CD‑ready (Drone).                                                      |

---

## 🗂️ Repository Structure

```text
serj-back
├── api/                     # 🔌  FastAPI routes
│   ├── bookings.py          # → Booking endpoints & queue dispatcher
│   ├── login.py             # → Telegram auth & token refresh
│   ├── places.py            # → Place search (FTS + trigram)
│   └── utils/               # 🛠️  shared helpers
│       ├── auth_tools.py    # → JWT / Telegram validation
│       ├── logger.py        # → struct‑log wrapper
│       └── schemas.py       # → Pydantic DTOs
├── database/                # 🗄️  ORM models & helpers
│   ├── database.py
│   ├── models.py
│   ├── import_data.py
│   └── parser_for_new_db.py
├── tasks.py                 # ⚙️  Celery task entry point
├── celery_app.py            # ⚙️  Celery workers / beat
├── celerybeat-schedule      # 🕒  generated schedule
├── config.py                # 🔧  Pydantic settings
├── main.py                  # 🚀  Uvicorn entry point
├── Dockerfile               # 🐳  Image
├── drone.yaml               # 🤖  CI pipeline
├── requirements.txt         # 📦  Dependencies
└── README.md                # 📚  You are here
```

> **Note:** `place.available_online` is **true** when the restaurant supports instant booking via **LeClick** (not banquet); otherwise it is `false`.

---

## 🔧 Environment Variables

Each environment variable configures part of the system:

| Variable                | Description                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------ |
| `UVICORN_HOST`          | Host address for the FastAPI server (e.g., `0.0.0.0` to listen on all interfaces).   |
| `HOST_QUEUE`            | IP address or domain of the RabbitMQ broker.                                         |
| `PORT_QUEUE`            | Port on which RabbitMQ is exposed (default is `5672`).                               |
| `USERNAME_QUEUE`        | Username for RabbitMQ authentication.                                                |
| `PASSWORD_QUEUE`        | Password for RabbitMQ authentication.                                                |
| `CALL_QUEUE`            | Queue name for restaurants requiring a phone call.                                   |
| `PARS_QUEUE`            | Queue name for restaurants that can be booked online.                                |
| `BOOKING_SUCCESS_STATE` | Internal marker for a successful booking status (e.g., `booked`).                    |
| `BOOKING_FAILURE_STATE` | Internal marker for a failed booking status (e.g., `failed`).                        |
| `GROQ_TOKEN`            | API token to authenticate requests to the Groq AI platform (used for LLM inference). |


---

## 🔗 REST Endpoints

| Method | Path                          | Auth     | Purpose                                         |
| ------ | ----------------------------- | -------- | ----------------------------------------------- |
| POST   | `/api/bookings`               | ✅        | Create a new booking & push to queue            |
| GET    | `/api/bookings`               | ✅        | List user bookings (upcoming / past / archived) |
| POST   | `/api/bookings/update_status` | Internal | Update booking status (success / failure)       |
| GET    | `/api/places`                 | — / ✅    | Search places (FTS + similarity)                |
| POST   | `/api/member`                 | —        | Login with Telegram `initData` & issue JWTs     |
| POST   | `/api/refresh`                | —        | Refresh JWT pair                                |
| GET    | `/api/protected`              | ✅        | Example protected route                         |
| GET    | `/api/member_phone`           | ✅        | Retrieve member's phone number                  |
| GET    | `/`                           | —        | Health check                                    |

### Queues

| Queue        | Used for                                               |
| ------------ | ------------------------------------------------------ |
| `PARS_QUEUE` | Online‑capable restaurants (`available_online = true`) |
| `CALL_QUEUE` | Restaurants requiring manual phone call                |

Celery workers subscribe with `prefetch_count = 1` to keep back‑pressure while the auto‑dialer or parser handles time‑consuming tasks.

