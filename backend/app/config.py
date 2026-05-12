from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    zadarma_key: str = ""
    zadarma_secret: str = ""
    manager_telegram_chat_id: str = ""
    admin_telegram_chat_id: str = ""
    storage_path: str = "/app/storage"
    frontend_url: str = "http://localhost:3000"

    # Окружение: "dev" / "prod". В prod webhook без подписи — отказ; pdf без WeasyPrint — отказ.
    environment: str = "dev"

    # При первом запуске на пустой БД создавать демо-аккаунты admin/manager/teacher.
    # Должно быть True ТОЛЬКО для dev/CI. В prod — False, и сидинг полностью пропускается.
    seed_demo_users: bool = False

    # Базовая сумма договора, если не задана иначе (₽/мес).
    default_contract_amount: float = 5000.0

    # Ограничение брутфорса /auth/login: попыток за окно (5 минут) с одного IP.
    # 30 даёт нормальному пользователю запас при опечатках, но блокирует брут.
    login_rate_limit_per_5min: int = 30

    class Config:
        env_file = ".env"


settings = Settings()

# SECRET_KEY должен быть случайным и достаточно длинным.
# Любой placeholder ("your-..." / "change-me" / короче 32 символов) — отказ.
_PLACEHOLDER_PREFIXES = ("your-", "change-", "placeholder", "secret-key")
if (
    len(settings.secret_key) < 32
    or any(settings.secret_key.lower().startswith(p) for p in _PLACEHOLDER_PREFIXES)
):
    raise RuntimeError(
        "SECRET_KEY должен быть длиной ≥32 символов и не являться placeholder. "
        "Сгенерируйте: openssl rand -hex 32"
    )
