"""Исключения для модуля синхронизации статей расходов."""


class ExpenseSyncBaseException(Exception):
    """Базовое исключение модуля синхронизации статей расходов."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ExpenseSyncRepositoryError(ExpenseSyncBaseException):
    """Ошибка при работе с хранилищем настроек/соответствий."""
