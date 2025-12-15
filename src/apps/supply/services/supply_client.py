"""Клиент для работы с поступлениями."""

from ..payable_document_base.services.base_client import BaseDocumentClient


class SupplyClient(BaseDocumentClient):
    """Клиент для работы с поступлениями."""

    @property
    def entity_type(self) -> str:
        return "supply"
