"""Pydantic схемы для работы со счетами поставщиков."""

from ..payable_document_base.schemas import BaseDocumentResponse

class InvoiceInResponse(BaseDocumentResponse):
    """Ответ API с информацией о счете поставщика."""

    pass
