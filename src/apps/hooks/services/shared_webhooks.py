"""Вебхуки, общие для нескольких фич.

МойСклад не даёт создать два вебхука с одинаковыми url/entityType/action,
поэтому, например, paymentout CREATE обслуживает и автопривязку, и
автопроставление статьи расходов. Выключать такой вебхук в МойСклад можно,
только если он не нужен ни одной другой фиче аккаунта, а включающая фича
должна включить его, даже если он уже существует, но выключен.
"""

import logging
from dataclasses import dataclass, field
from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...expense_sync.constants import (
    EXPENSE_PAYMENT_ENTITY_TYPES,
    EXPENSE_PAYMENT_WEBHOOK_ACTION,
)
from ...expense_sync.models import ExpenseItemSyncConfig
from ...income_sync.constants import (
    INCOME_PAYMENT_ENTITY_TYPES,
    INCOME_PAYMENT_WEBHOOK_ACTION,
)
from ...income_sync.models import IncomeItemSyncConfig
from .moysklad_client import MoySkladClient

logger = logging.getLogger(__name__)


async def is_used_by_other_features(
    session: AsyncSession, account_id: str, entity_type: str, action: str
) -> bool:
    """Нужен ли вебхук какой-либо фиче аккаунта, кроме автопривязки."""
    if (
        entity_type in EXPENSE_PAYMENT_ENTITY_TYPES
        and action == EXPENSE_PAYMENT_WEBHOOK_ACTION
    ):
        stmt = select(ExpenseItemSyncConfig.id).where(
            ExpenseItemSyncConfig.ms_account_id == account_id,
            ExpenseItemSyncConfig.enabled.is_(True),
            ExpenseItemSyncConfig.counterparty_attribute_id.is_not(None),
        )
        if await session.scalar(stmt) is not None:
            return True

    if (
        entity_type in INCOME_PAYMENT_ENTITY_TYPES
        and action == INCOME_PAYMENT_WEBHOOK_ACTION
    ):
        stmt = select(IncomeItemSyncConfig.id).where(
            IncomeItemSyncConfig.ms_account_id == account_id,
            IncomeItemSyncConfig.enabled.is_(True),
            IncomeItemSyncConfig.counterparty_attribute_id.is_not(None),
        )
        if await session.scalar(stmt) is not None:
            return True

    return False


@dataclass
class EnsureWebhooksResult:
    """Итог приведения вебхуков к состоянию «существует и включён»."""

    created: int = 0
    enabled: int = 0
    existing: int = 0
    errors: List[str] = field(default_factory=list)


async def ensure_webhooks_enabled(
    client: MoySkladClient, url: str, required: Iterable[tuple[str, str]]
) -> EnsureWebhooksResult:
    """Создать недостающие и включить выключенные вебхуки (entityType, action)."""
    result = EnsureWebhooksResult()

    try:
        existing = await client.list_webhooks()
    except Exception as exc:  # pragma: no cover - сетевые ошибки
        result.errors.append(f"Не удалось получить список вебхуков: {exc}")
        logger.warning("Не удалось получить список вебхуков: %s", exc)
        existing = []

    by_key = {(w.get("entityType"), w.get("action"), w.get("url")): w for w in existing}

    for entity_type, action in required:
        webhook = by_key.get((entity_type, action, url))
        try:
            if webhook is None:
                await client.create_webhook(
                    entity_type=entity_type, action=action, url=url
                )
                result.created += 1
            elif webhook.get("enabled") is False:
                await client.update_webhook(webhook_data=webhook, enabled=True)
                result.enabled += 1
                logger.info(
                    "Включён ранее выключенный вебхук %s/%s (id=%s)",
                    entity_type,
                    action,
                    webhook.get("id"),
                )
            else:
                result.existing += 1
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            msg = f"Не удалось включить вебхук {entity_type}/{action}: {exc}"
            result.errors.append(msg)
            logger.warning(msg)

    return result
