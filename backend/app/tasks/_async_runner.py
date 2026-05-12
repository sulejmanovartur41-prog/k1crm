"""Helper для запуска async-кода внутри Celery-таска.

Глобальный `engine`/`async_session_maker` создаются в master-процессе FastAPI и
привязаны к его event-loop'у. Использование их в Celery worker (другой процесс,
другой loop) приводит к ошибкам `Future attached to a different loop` и утечкам
соединений. Поэтому здесь мы создаём отдельный engine на каждый запуск таска
и корректно закрываем его в `finally`.
"""
import asyncio
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

SessionFactory = async_sessionmaker[AsyncSession]


def run_async_task(coro_factory: Callable[[SessionFactory], Awaitable[None]]) -> None:
    """Создаёт fresh async engine, отдаёт session_maker в callable, корректно закрывает.

    Использование:
        def my_celery_task():
            async def _run(session_maker):
                async with session_maker() as db:
                    ...
            run_async_task(_run)
    """
    async def _runner() -> None:
        engine = create_async_engine(settings.database_url, echo=False)
        session_maker: SessionFactory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        try:
            await coro_factory(session_maker)
        finally:
            await engine.dispose()

    asyncio.run(_runner())
