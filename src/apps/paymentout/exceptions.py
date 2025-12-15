"""Исключения для работы с входящими платежами."""


class PaymentOutBaseException(Exception):
    """Базовое исключение для входящих платежей."""
    
    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class PaymentOutNotFoundError(PaymentOutBaseException):
    """Входящий платеж не найден."""


class PaymentOutAPIError(PaymentOutBaseException):
    """Ошибка при работе с API входящих платежей."""