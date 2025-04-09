# Базовый образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем FastAPI и Uvicorn
RUN pip install --no-cache-dir fastapi uvicorn

# Копируем код
COPY . /app

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
