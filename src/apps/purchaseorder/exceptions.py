"""Исключения для работы с заказами покупателя."""


class PurchaseOrderBaseException(Exception):
    """Базовое исключение для заказов покупателя."""
    
    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class PurchaseOrderNotFoundError(PurchaseOrderBaseException):
    """Заказ покупателя не найден."""


class PurchaseOrderAPIError(PurchaseOrderBaseException):
    """Ошибка при работе с API заказов покупателя."""