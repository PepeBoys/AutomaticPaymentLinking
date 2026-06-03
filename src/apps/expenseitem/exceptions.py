"""Исключения для работы со статьями расходов."""


class ExpenseItemBaseException(Exception):
    """Базовое исключение для статей расходов."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ExpenseItemNotFoundError(ExpenseItemBaseException):
    """Статья расходов не найдена."""


class ExpenseItemAPIError(ExpenseItemBaseException):
    """Ошибка при работе с API статей расходов."""
