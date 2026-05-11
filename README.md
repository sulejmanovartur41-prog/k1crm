# KiberOne CRM

Информационная система управления школой программирования KiberOne. Автоматизирует полный цикл работы с учеником: от первого обращения до ежемесячной оплаты.

## Стек технологий

**Бэкенд**
- Python 3.11 · FastAPI 0.110 · SQLAlchemy 2.0 async (asyncpg)
- Alembic (миграции) · Celery 5.3 + Redis 7 (фоновые задачи)
- Pydantic v2 · python-jose (JWT) · passlib + bcrypt (пароли)
- WeasyPrint + Jinja2 (генерация PDF-договоров)
- python-telegram-bot 20.x (Telegram-бот, webhook)
- Zadarma API (click-to-call)

**Фронтенд**
- React 18 · TypeScript · Vite 5
- Ant Design 5 · React Query · Recharts
- React Router v6

**Мобильное приложение** (для преподавателей)
- React Native 0.73 · Expo 50

**Инфраструктура**
- Docker Compose · Nginx (reverse proxy)
- PostgreSQL 16

## Бизнес-процессы

| Процесс | Описание |
|---|---|
| A1 — Сбор лидов | Telegram-бот, форма на сайте, ручной ввод |
| A2 — Обработка звонков | Очередь задач, Zadarma click-to-call, фиксация итогов |
| A3 — Пробный урок и договор | Бронирование, напоминания, PDF-договор, подписание |
| A4 — Сопровождение клиента | Посещаемость, оплата, уведомления о долгах |

## Быстрый старт

### Требования
- Docker Desktop
- Docker Compose

### 1. Клонировать репозиторий

```bash
git clone https://github.com/sulejmanovartur41-prog/k1crm.git
cd k1crm
```

### 2. Создать файл `.env`

```env
DATABASE_URL=postgresql+asyncpg://kibrone:password@postgres:5432/kibrone
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key-min-32-chars

# Опционально
TELEGRAM_BOT_TOKEN=
ZADARMA_KEY=
ZADARMA_SECRET=
MANAGER_TELEGRAM_CHAT_ID=
ADMIN_TELEGRAM_CHAT_ID=
FRONTEND_URL=http://localhost:3000
```

### 3. Запустить

```bash
docker-compose up --build
```

Сервисы будут доступны по адресам:

| Адрес | Сервис |
|---|---|
| http://localhost | Фронтенд (через Nginx) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:3000 | Vite dev server |

### Дефолтные учётные записи

| Логин | Пароль | Роль |
|---|---|---|
| `admin` | `admin123` | Администратор |
| `manager` | `manager123` | Менеджер |
| `teacher` | `teacher123` | Преподаватель |

## Структура проекта

```
kibrone/
├── backend/
│   ├── alembic/              # Миграции БД
│   ├── app/
│   │   ├── api/v1/           # REST-эндпоинты
│   │   ├── bot/              # Telegram-бот
│   │   ├── models/           # SQLAlchemy модели
│   │   ├── services/         # PDF, уведомления, телефония
│   │   ├── tasks/            # Celery-задачи
│   │   ├── templates/        # Jinja2 шаблоны (PDF)
│   │   └── tests/            # Pytest тесты
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/              # Typed API-клиенты
│   │   ├── components/       # AppLayout
│   │   └── pages/            # leads, payments, schedule, ...
│   └── Dockerfile
├── mobile/
│   └── app/                  # Expo Router экраны
├── nginx/
│   └── nginx.conf
└── docker-compose.yml
```

## API

Полная документация доступна в Swagger UI: **http://localhost:8000/docs**

Основные группы эндпоинтов:

- `POST /api/v1/auth/login` — получить JWT
- `GET/POST /api/v1/leads` — управление лидами
- `GET/POST /api/v1/calls/tasks` — очередь звонков
- `POST /api/v1/calls/result` — зафиксировать итог звонка
- `GET /api/v1/schedule/lessons` — расписание занятий
- `POST /api/v1/contracts/intake` — анкета нового клиента
- `POST /api/v1/contracts/{id}/sign` — подписать договор
- `POST /api/v1/attendance/lessons/{id}/mark` — отметить посещаемость
- `GET/POST /api/v1/payments` — платежи
- `GET /api/v1/payments/dashboard` — аналитика

## Тесты

```bash
docker-compose exec backend python -m pytest app/tests/ -v
```

```
11 passed in 11.40s
```

Тесты покрывают: создание лида и авто-задачи, статусы лида, посещаемость, договоры (intake / sign / невалидный токен), платежи и дашборд.

## Telegram-бот

Бот принимает входящие сообщения и автоматически создаёт лида в CRM. Для подключения:

1. Создайте бота через @BotFather, получите токен
2. Укажите `TELEGRAM_BOT_TOKEN` в `.env`
3. Зарегистрируйте webhook:
   ```
   POST https://api.telegram.org/bot<TOKEN>/setWebhook
   {"url": "https://your-domain.com/api/v1/bot/webhook"}
   ```
