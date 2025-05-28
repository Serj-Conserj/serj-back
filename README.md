# Conserj.ru: AI-powered Table Reservation Service

Conserj.ru is an intelligent online booking platform that allows users to reserve tables in Moscow restaurants seamlessly through a combination of web interface, Telegram bot integration, and AI-powered phone calls. The system minimizes user input, automates the booking process, and provides real-time updates.

## Features

* **Smart Booking Engine**: Uses both online APIs and AI-driven phone calls to place reservations.
* **Telegram Bot Authentication**: Quick user login and data collection via Telegram.
* **Fast Booking Interface**: Minimal UI allows booking in under a minute.
* **Hybrid Booking Workflow**: Automatically chooses the best method (API or call) for each restaurant.
* **Admin Dashboard**: Monitor bookings, manage restaurants, and analyze usage.

## Technologies Used

* **Backend**: FastAPI (Python)
* **Database**: PostgreSQL
* **Task Queues**: RabbitMQ
* **Scheduled Jobs**: Celery
* **Voice Call Handling**: SIP + AI for speech processing
* **Infrastructure**: Docker + Drone CI for deployments

## Architecture

* **Microservice-based**
* **Booking Requests** are routed via RabbitMQ to either:

  * Online integration handler (if API is available)
  * SIP-based AI call handler (if no integration exists)
* **Periodic Updaters** using Celery keep restaurant data current
* **Prometheus + Grafana** monitor system health and performance

## Setup

To run the system locally:

```bash
git clone https://github.com/Serj-Conserj/serj-back.git
cd serj-back
docker compose up --build
```

Ensure the following directories are mounted correctly for config, data, and provisioning.

## Telegram Bot Flow

1. User visits [https://conserj.ru](https://conserj.ru)
2. Redirect to Telegram Bot for login
3. Telegram provides name, phone — stored automatically
4. Booking made with zero form-filling from user

## AI Calling Workflow

1. System initiates SIP call with reservation details
2. Records response, sends to ML model for interpretation
3. Model processes and responds via voice if needed
4. Result recorded and user is notified via bot/website

## Project Status

The project is actively developed as part of a HSE Bachelor's programme and participated in MTS TrueTech Hack and VK Education Summer School. It combines real-time systems, NLP, and user-centric design for solving a real-world problem.

## Demo

Live at [https://conserj.ru](https://conserj.ru)
