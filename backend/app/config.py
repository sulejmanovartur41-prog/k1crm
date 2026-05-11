from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    telegram_bot_token: str = ""
    zadarma_key: str = ""
    zadarma_secret: str = ""
    manager_telegram_chat_id: str = ""
    admin_telegram_chat_id: str = ""
    storage_path: str = "/app/storage"
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
