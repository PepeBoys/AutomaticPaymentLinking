"""Исключения для работы с приходными ордерами."""


class CashOutBaseException(Exception):
    """Базовое исключение для приходных ордеров."""
    
    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class CashOutNotFoundError(CashOutBaseException):
    """Приходный ордер не найден."""


class CashOutAPIError(CashOutBaseException):
    """Ошибка при работе с API приходных ордеров."""