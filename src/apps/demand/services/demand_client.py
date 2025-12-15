"""Клиент для работы с отгрузками."""

from ...payable_document_base.services.base_client import BaseDocumentClient


class DemandClient(BaseDocumentClient):
    """Клиент для работы с отгрузками."""

    @property
    def entity_type(self) -> str:
        return "demand"
