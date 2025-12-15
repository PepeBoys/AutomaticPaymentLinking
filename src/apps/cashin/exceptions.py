"""Исключения для работы с приходными ордерами."""


class CashInBaseException(Exception):
    """Базовое исключение для приходных ордеров."""
    
    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class CashInNotFoundError(CashInBaseException):
    """Приходный ордер не найден."""


class CashInAPIError(CashInBaseException):
    """Ошибка при работе с API приходных ордеров."""