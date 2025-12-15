"""Клиент для работы с API счетов поставщиков МойСклад."""

from ...payable_document_base.services.base_client import BaseDocumentClient


class InvoiceInClient(BaseDocumentClient):
    """Клиент для работы с API счетов поставщиков."""

    @property
    def entity_type(self) -> str:
        return "invoicein"
