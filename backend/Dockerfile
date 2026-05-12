# === Stage 1: builder ===
# Нужен gcc + libpq-dev для компиляции asyncpg, psycopg2 и других C-расширений.
# В финальный образ эти инструменты не попадают.
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# === Stage 2: runtime ===
# Только runtime-библиотеки: нет компилятора, нет заголовков.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpq5 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные пакеты из builder — без исходников и компилятора
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Не запускаем uvicorn от root
RUN useradd -m -u 1000 appuser

WORKDIR /app
RUN mkdir -p /app/storage && chown -R appuser /app

COPY --chown=appuser . .

USER appuser

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
