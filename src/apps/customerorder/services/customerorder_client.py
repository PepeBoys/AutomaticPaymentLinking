"""Клиент для работы с заказами покупателей."""

from ..payable_document_base.services.base_client import BaseDocumentClient


class CustomerOrderClient(BaseDocumentClient):
    """Клиент для работы с заказами покупателей."""

    @property
    def entity_type(self) -> str:
        return "customerorder"
