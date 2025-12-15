"""Базовые исключения для оплачиваемых документов."""


class BaseDocumentException(Exception):
    """Базовое исключение для документов."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DocumentNotFoundError(BaseDocumentException):
    """Документ не найден."""


class DocumentAPIError(BaseDocumentException):
    """Ошибка при работе с API документов."""
