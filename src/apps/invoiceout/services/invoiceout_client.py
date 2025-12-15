"""Клиент для работы с API счетов покупателю МойСклад."""

from ...payable_document_base.services.base_client import BaseDocumentClient


class InvoiceOutClient(BaseDocumentClient):
    """Клиент для работы с API счетов покупателю."""

    @property
    def entity_type(self) -> str:
        return "invoiceout"
