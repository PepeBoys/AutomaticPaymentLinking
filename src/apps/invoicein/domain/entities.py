"""Доменные сущности счетов поставщиков."""

from dataclasses import dataclass

from ...payable_document_base.domain.entities import BasePayableDocumentEntity


@dataclass
class InvoiceInEntity(BasePayableDocumentEntity):
    """Доменная сущность счета поставщика."""

    pass
