"""Доменные сущности счетов покупателю."""

from dataclasses import dataclass

from ...payable_document_base.domain.entities import BasePayableDocumentEntity


@dataclass
class InvoiceOutEntity(BasePayableDocumentEntity):
    """Доменная сущность счета покупателю."""

    pass
