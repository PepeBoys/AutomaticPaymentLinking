"""Исключения для работы с контрагентами."""


class CounterpartyBaseException(Exception):
    """Базовое исключение для контрагентов."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class CounterpartyNotFoundError(CounterpartyBaseException):
    """Контрагент не найден."""


class CounterpartyAPIError(CounterpartyBaseException):
    """Ошибка при работе с API контрагентов."""
