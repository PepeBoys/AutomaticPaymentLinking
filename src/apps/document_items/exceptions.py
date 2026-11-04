"""Исключения модуля статей в первичных документах."""


class DocumentItemsBaseException(Exception):
    """Базовое исключение модуля."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DocumentItemsAPIError(DocumentItemsBaseException):
    """Ошибка при работе с API МойСклад."""
