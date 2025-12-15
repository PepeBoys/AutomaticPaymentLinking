"""Исключения для работы с отгрузками (supply)."""


class SupplyBaseException(Exception):
    """Базовое исключение для отгрузок."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SupplyNotFoundError(SupplyBaseException):
    """Отгрузка не найдена."""


class SupplyAPIError(SupplyBaseException):
    """Ошибка при работе с API отгрузок."""