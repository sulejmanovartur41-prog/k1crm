import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine
from app.api.v1 import auth, leads, calls, schedule, contracts, attendance, payments, groups

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def seed_default_users():
    """Создаёт демо-аккаунты admin/manager/teacher.

    Запускается ТОЛЬКО если settings.seed_demo_users=True (по умолчанию False).
    Это защита от того, чтобы prod-инстанс с публичным IP не запускался
    с известными паролями `admin123` и т.д.
    """
    from sqlalchemy import select
    from app.database import async_session_maker
    from app.models.user import User
    from app.api.v1.auth import hash_password

    if not settings.seed_demo_users:
        logger.info("Demo users seeding skipped (SEED_DEMO_USERS=false)")
        return

    defaults = [
        {"role": "admin", "name": "Администратор", "login": "admin", "password": "admin123"},
        {"role": "manager", "name": "Менеджер", "login": "manager", "password": "manager123"},
        {"role": "teacher", "name": "Преподаватель", "login": "teacher", "password": "teacher123"},
    ]
    try:
        async with async_session_maker() as db:
            for u in defaults:
                result = await db.execute(select(User).where(User.login == u["login"]))
                if not result.scalar_one_or_none():
                    db.add(User(
                        role=u["role"],
                        name=u["name"],
                        login=u["login"],
                        password_hash=hash_password(u["password"]),
                    ))
            await db.commit()
        logger.info("Default users seeded (dev mode)")
    except Exception as e:
        logger.warning("Could not seed default users (DB may not be ready): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.storage_path, exist_ok=True)
    await seed_default_users()
    logger.info("KiberOne backend started")
    yield
    await engine.dispose()
    logger.info("KiberOne backend stopped")


app = FastAPI(
    title="KiberOne CRM",
    description="Информационная система управления школой программирования KiberOne",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — в prod строго один frontend_url; в dev допускаются localhost.
_cors_origins = [settings.frontend_url]
if settings.environment == "dev":
    _cors_origins += ["http://localhost:3000", "http://localhost"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("%s %s", request.method, request.url.path)
    response = await call_next(request)
    return response


# Register routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(leads.router, prefix="/api/v1")
app.include_router(calls.router, prefix="/api/v1")
app.include_router(schedule.router, prefix="/api/v1")
app.include_router(contracts.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(groups.router, prefix="/api/v1")


# Telegram bot webhook — проверяем secret_token, выставленный при setWebhook
@app.post("/api/v1/bot/webhook", tags=["bot"])
async def telegram_webhook(request: Request):
    from telegram import Update
    from app.bot.handler import create_bot_application
    bot_app = create_bot_application()
    if bot_app is None:
        return JSONResponse({"status": "bot not configured"})

    # X-Telegram-Bot-Api-Secret-Token задаётся через setWebhook?secret_token=...
    # Должен содержать только [A-Za-z0-9_-], длина 1..256.
    expected = settings.telegram_webhook_secret
    got = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if expected and got != expected:
        return JSONResponse({"status": "forbidden"}, status_code=403)

    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return JSONResponse({"status": "ok"})


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "KiberOne CRM"}
