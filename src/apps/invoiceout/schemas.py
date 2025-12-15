"""Pydantic схемы для работы со счетами покупателю."""

from ..payable_document_base.schemas import BaseDocumentResponse

class InvoiceOutResponse(BaseDocumentResponse):
    """Ответ API с информацией о счете покупателю."""

    pass
