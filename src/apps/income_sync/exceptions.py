"""Исключения для модуля автопроставления статьи доходов."""


class IncomeSyncBaseException(Exception):
    """Базовое исключение модуля автопроставления статьи доходов."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class IncomeSyncRepositoryError(IncomeSyncBaseException):
    """Ошибка при работе с хранилищем настроек."""
