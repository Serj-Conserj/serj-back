# Conserj.ru – AI-Based Restaurant Reservation Service

## Overview

Conserj.ru is a smart concierge system for booking tables in Moscow restaurants. It combines Telegram authentication, automated voice booking via SIP, online API integrations, Prometheus monitoring, ClickHouse analytics, and a hybrid task queue powered by RabbitMQ.

## Features

* **Web + Telegram Web App** interface
* **Fast restaurant search** with filters (location, cuisine, price)
* **Booking via API** (if supported by restaurant)
* **Booking via automated call** (if no API)
* **AI voice model for call handling**
* **Metrics tracking** via Prometheus
* **Analytics dashboard** via Grafana + ClickHouse

## Tech Stack

* **Backend**: FastAPI
* **Database**: PostgreSQL
* **Asynchronous Tasks**: Celery + RabbitMQ
* **Voice Calls**: SIP + TTS/ASR/LLM
* **Monitoring**: Prometheus + Grafana
* **Analytics**: ClickHouse cluster
* **CI/CD**: Drone CI
* **Auth**: Telegram Login
* **DevOps**: Docker Compose, Consul, Zookeeper

## System Architecture

* PostgreSQL stores users, restaurants, and booking data.
* RabbitMQ has two queues: `Online` (API bookings) and `Calling` (SIP phone bot).
* ClickHouse stores real-time metrics and events.
* Prometheus collects metrics (saves, updates, errors) and exposes on port 84.
* Grafana reads from ClickHouse to visualize performance.
* Consul handles service discovery and leader election.

## Folder Structure

```
.
├── clickhouse/          # Cluster config and node setup
├── grafana/             # Dashboards, datasources, provisioning
├── microservice/        # Event simulation logic, ClickHouse writes
├── prometheus/          # Config + persistent volume
├── docker-compose.yml   # Main orchestration file
```

## Getting Started

### 1. Launch All Services

```bash
docker compose up --build
```

### 2. Access Interfaces

* **Grafana**: [http://localhost:3000](http://localhost:3000) (admin / admin123)
* **Prometheus**: [http://localhost:9090](http://localhost:9090)
* **ClickHouse (Web UI)**: [http://localhost:8124](http://localhost:8124) (user/pass: default)
* **Consul UI**: [http://localhost:8500](http://localhost:8500)

### 3. View Metrics

* Run the event simulator (`microservice/`) to stream synthetic data.
* Metrics are exposed at `http://localhost:84/metrics`
* Use prebuilt Grafana dashboards for visualization.

## Contributors

* Sergey Budygin – Backend, ClickHouse, Prometheus, Docker, GitOps
* Pavel Sardak – Data scraping, PostgreSQL model design
* Maxim Kuptsov – Frontend, UI/UX, Telegram Web App integration

## License

MIT (or academic use only – project for HSE Bachelor in DSBA)

---

> This project was created as part of the 2nd year Software Team Project course at the Higher School of Economics, Faculty of Computer Science.
