"""Проставление статьи доходов/расходов в документы, к которым привязан платёж.

Вызывается после успешной автопривязки: берёт статью из доп. поля контрагента
платежа и ставит её в доп. поле «Статья доходов» / «Статья расходов» документов
привязки (режим linked) или всей их цепочки — заказ, его счета и
отгрузки/приёмки (режим chain). Заполненную статью в документе не меняет.
"""

import logging
from typing import Any, Dict, Optional

from ...expense_sync.uow.unit_of_work import ExpenseSyncUnitOfWork
from ...income_sync.uow.unit_of_work import IncomeSyncUnitOfWork
from ...ms_auth.services.auth_service import MySkladAuthService
from ..constants import (
    CHAIN_LINK_FIELDS,
    DOCUMENT_LABELS,
    EXPENSE_DOCUMENT_TYPES,
    INCOME_DOCUMENT_TYPES,
    MODE_CHAIN,
    MODE_OFF,
)
from ..exceptions import DocumentItemsAPIError
from ..repository import DocumentItemsConfigRepository, attribute_field
from .client import DocumentItemsClient

logger = logging.getLogger(__name__)

ORDER_TYPES = ("customerorder", "purchaseorder")


def _attribute_value(entity: Dict[str, Any], attribute_id: str) -> Optional[Any]:
    for attr in entity.get("attributes", []) or []:
        if attr.get("id") == attribute_id:
            return attr.get("value")
    return None


def _linked_refs(entity: Dict[str, Any]) -> list[tuple[str, str]]:
    """(type, href) документов цепочки из полей customerOrder, invoicesOut, demands и т.п."""
    refs = []
    for field_name in CHAIN_LINK_FIELDS:
        value = entity.get(field_name)
        for item in value if isinstance(value, list) else [value] if value else []:
            meta = item.get("meta", {})
            if meta.get("href") and meta.get("type"):
                refs.append((meta["type"], meta["href"]))
    return refs


class DocumentItemsHandler:
    def __init__(self, auth_service: MySkladAuthService, session) -> None:
        self._configs = DocumentItemsConfigRepository(session)
        self._income = IncomeSyncUnitOfWork(session)
        self._expense = ExpenseSyncUnitOfWork(session)
        self._client = DocumentItemsClient(auth_service)

    async def apply_after_linking(
        self, account_id: str, payment_href: str, outgoing: bool
    ) -> None:
        """Проставить статью в документы привязки. Не бросает исключений."""
        try:
            await self._apply(account_id, payment_href, outgoing)
        except DocumentItemsAPIError as exc:
            logger.warning(
                "Статья в документы не проставлена (платёж %s): %s %s",
                payment_href,
                exc.message,
                exc.details,
            )

    async def _apply(self, account_id: str, payment_href: str, outgoing: bool) -> None:
        config = await self._configs.get(account_id)
        mode = (config.expense_mode if outgoing else config.income_mode) if config else MODE_OFF
        if mode == MODE_OFF:
            return

        document_types = EXPENSE_DOCUMENT_TYPES if outgoing else INCOME_DOCUMENT_TYPES
        side = "расходов" if outgoing else "доходов"
        sync_config = await (
            self._expense if outgoing else self._income
        ).configs.get_by_account_id(account_id)
        if not sync_config or not sync_config.is_initialized:
            return

        payment = await self._client.get_by_href(payment_href)
        agent_meta = (payment or {}).get("agent", {}).get("meta", {})
        if not payment or agent_meta.get("type") != "counterparty":
            return

        counterparty = await self._client.get_by_href(agent_meta["href"])
        value = _attribute_value(counterparty or {}, sync_config.counterparty_attribute_id)
        element_href = (value or {}).get("meta", {}).get("href") if isinstance(value, dict) else None
        if not element_href:
            logger.info(
                "У контрагента %s не заполнена статья %s, в документы не проставляем",
                agent_meta["href"].rsplit("/", 1)[-1],
                side,
            )
            return

        targets: dict[str, str] = {}  # href -> type
        for operation in payment.get("operations", []) or []:
            meta = operation.get("meta", {})
            if meta.get("type") in document_types:
                targets[meta["href"]] = meta["type"]
                if mode == MODE_CHAIN:
                    await self._add_chain(meta["type"], meta["href"], document_types, targets)

        for href, document_type in targets.items():
            await self._stamp(config, document_type, href, element_href, side, value.get("name"))

    async def _add_chain(
        self, document_type: str, href: str, document_types: tuple, targets: dict
    ) -> None:
        """Добавить документы цепочки: заказ (корень) и связанные с ним и с документом."""
        document = await self._client.get_by_href(href)
        if not document:
            return
        refs = _linked_refs(document)
        if document_type not in ORDER_TYPES:
            root_href = next((h for t, h in refs if t in ORDER_TYPES), None)
            root = await self._client.get_by_href(root_href) if root_href else None
            if root:
                refs += _linked_refs(root)
        for ref_type, ref_href in refs:
            if ref_type in document_types:
                targets.setdefault(ref_href, ref_type)

    async def _stamp(
        self, config, document_type: str, href: str, element_href: str, side: str, item_name
    ) -> None:
        attribute_id = getattr(config, attribute_field(document_type))
        if not attribute_id:
            return
        document = await self._client.get_by_href(href)
        if not document:
            return
        if _attribute_value(document, attribute_id):
            logger.info(
                "Статья %s у %s %s уже заполнена, не меняем",
                side,
                DOCUMENT_LABELS[document_type],
                document.get("name"),
            )
            return
        await self._client.set_customentity_attribute(
            document_type, document["id"], attribute_id, element_href
        )
        logger.info(
            "✓ Статья %s '%s' проставлена в доп. поле %s %s",
            side,
            item_name,
            DOCUMENT_LABELS[document_type],
            document.get("name"),
        )
