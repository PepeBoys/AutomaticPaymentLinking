from asyncio import current_task
from typing import AsyncGenerator

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings


class DatabaseManager:
    """Менеджер для управления подключением к БД и сессиями."""

    def __init__(self, url: str, echo: bool = False) -> None:
        self.engine = create_async_engine(
            url=url,
            echo=echo,
            future=True,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )
    
    def get_scope_session(self) -> async_scoped_session:
        """Получить scoped сессию для текущей задачи."""
        return async_scoped_session(
            session_factory=self.session_factory,
            scopefunc=current_task,
        )

    async def session_dependency(self) -> AsyncGenerator[AsyncSession, None]:
        """Dependency для получения обычной сессии."""
        async with self.session_factory() as session:
            yield session
            await session.close()

    async def scope_session_dependency(self) -> AsyncGenerator[AsyncSession, None]:
        """Dependency для получения scoped сессии."""
        session = self.get_scope_session()
        try:
            yield session
        finally:
            await session.close()


db_manager = DatabaseManager(
    url=settings.database_url,
    echo=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для FastAPI."""
    async for session in db_manager.session_dependency():
        yield session


async def init_db() -> None:
    """Инициализация БД."""
    import src.apps.hooks.models

    from .models import Base

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_apply_manual_migrations)


def _apply_manual_migrations(sync_conn) -> None:
    """Простые ручные миграции для поддержания схемы."""

    inspector = inspect(sync_conn)

    if "webhooksubscriptions" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("webhooksubscriptions")}
        if "payment_purpose_mask" not in columns:
            sync_conn.exec_driver_sql(
                "ALTER TABLE webhooksubscriptions "
                "ADD COLUMN payment_purpose_mask VARCHAR(512)"
            )

        new_status_columns = {
            "payment_status_on_success": "ALTER TABLE webhooksubscriptions ADD COLUMN payment_status_on_success VARCHAR(64)",
            "payment_status_on_failure": "ALTER TABLE webhooksubscriptions ADD COLUMN payment_status_on_failure VARCHAR(64)",
            "document_status_on_success": "ALTER TABLE webhooksubscriptions ADD COLUMN document_status_on_success VARCHAR(64)",
            "document_status_on_failure": "ALTER TABLE webhooksubscriptions ADD COLUMN document_status_on_failure VARCHAR(64)",
        }

        for column_name, ddl in new_status_columns.items():
            if column_name not in columns:
                sync_conn.exec_driver_sql(ddl)