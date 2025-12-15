"""Исключения для работы с расходными ордерами."""


class CashOutBaseException(Exception):
    """Базовое исключение для расходных ордеров."""
    
    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class CashOutNotFoundError(CashOutBaseException):
    """Расходный ордер не найден."""


class CashOutAPIError(CashOutBaseException):
    """Ошибка при работе с API расходных ордеров."""
