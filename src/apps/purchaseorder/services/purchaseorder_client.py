"""Клиент для работы с заказами поставщикам."""

from ..payable_document_base.services.base_client import BaseDocumentClient


class PurchaseOrderClient(BaseDocumentClient):
    """Клиент для работы с заказами поставщикам."""

    @property
    def entity_type(self) -> str:
        return "purchaseorder"
