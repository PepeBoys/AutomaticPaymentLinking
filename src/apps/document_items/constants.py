"""Константы модуля статей доходов/расходов в первичных документах."""

# Документы, к которым привязываются входящие платежи (статья доходов)
# и исходящие (статья расходов).
INCOME_DOCUMENT_TYPES = ("customerorder", "invoiceout", "demand")
EXPENSE_DOCUMENT_TYPES = ("purchaseorder", "invoicein", "supply")
DOCUMENT_TYPES = INCOME_DOCUMENT_TYPES + EXPENSE_DOCUMENT_TYPES

INCOME_ATTRIBUTE_NAME = "Статья доходов"
EXPENSE_ATTRIBUTE_NAME = "Статья расходов"

DOCUMENT_LABELS = {
    "customerorder": "заказа покупателя",
    "invoiceout": "счёта покупателю",
    "demand": "отгрузки",
    "purchaseorder": "заказа поставщику",
    "invoicein": "счёта поставщика",
    "supply": "приёмки",
}

# Режимы проставления статьи в документы.
MODE_OFF = "off"  # не проставлять
MODE_LINKED = "linked"  # только в документы, к которым привязан платёж
MODE_CHAIN = "chain"  # во все документы цепочки (заказ, его счета и отгрузки/приёмки)
MODES = (MODE_OFF, MODE_LINKED, MODE_CHAIN)

# Поля документа МС со ссылками на связанные документы цепочки.
CHAIN_LINK_FIELDS = (
    "customerOrder",
    "purchaseOrder",
    "invoicesOut",
    "invoicesIn",
    "demands",
    "supplies",
)
