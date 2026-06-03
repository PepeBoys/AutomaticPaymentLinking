"""Исключения для работы с пользовательскими справочниками."""


class CustomEntityBaseException(Exception):
    """Базовое исключение для пользовательских справочников."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class CustomEntityNotFoundError(CustomEntityBaseException):
    """Справочник или его элемент не найден."""


class CustomEntityAPIError(CustomEntityBaseException):
    """Ошибка при работе с API пользовательских справочников."""
