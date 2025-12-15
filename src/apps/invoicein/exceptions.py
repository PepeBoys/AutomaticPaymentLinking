"""Исключения для работы со счетами покупателю."""


class InvoiceInBaseException(Exception):
    """Базовое исключение для счетов покупателю."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class InvoiceInNotFoundError(InvoiceInBaseException):
    """Счет покупателю не найден."""


class InvoiceInAPIError(InvoiceInBaseException):
    """Ошибка при работе с API счетов покупателю."""