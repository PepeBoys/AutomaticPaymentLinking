"""Доменные сущности заказов поставщикам."""

from dataclasses import dataclass

from ...payable_document_base.domain.entities import BasePayableDocumentEntity


@dataclass
class PurchaseOrderEntity(BasePayableDocumentEntity):
    """Доменная сущность заказа поставщику."""

    pass
