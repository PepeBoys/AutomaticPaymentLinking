"""Базовые исключения для платежных документов."""


class BasePaymentException(Exception):
    """Базовое исключение для платежей."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class PaymentNotFoundError(BasePaymentException):
    """Платеж не найден."""


class PaymentAPIError(BasePaymentException):
    """Ошибка при работе с API платежей."""
