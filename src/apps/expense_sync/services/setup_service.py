"""Инициализация инфраструктуры синхронизации статей расходов.

Создаёт пользовательский справочник-зеркало статей расходов, наполняет его
текущими статьями (бэкафилл + локальные соответствия), создаёт доп. поле
контрагента, ссылающееся на этот справочник, и регистрирует вебхуки для
двусторонней синхронизации.

Операция идемпотентна: повторный запуск не создаёт дубликатов справочника,
доп. поля или элементов (уже сопоставленные статьи пропускаются).
"""

import logging
from dataclasses import dataclass, field
from typing import List

from src.core.config import settings

from ...counterparty.services.counterparty_service import CounterpartyService
from ...customentity.services.customentity_service import CustomEntityService
from ...expenseitem.services.expenseitem_service import ExpenseItemService
from ...ms_auth.services.auth_service import MySkladAuthService
from ..constants import (
    COUNTERPARTY_ATTRIBUTE_NAME,
    CUSTOMENTITY_ENTITY_TYPE,
    EXPENSE_PAYMENT_ENTITY_TYPES,
    EXPENSE_PAYMENT_WEBHOOK_ACTION,
    EXPENSEITEM_ENTITY_TYPE,
    MIRROR_DICTIONARY_NAME,
    SYNC_WEBHOOK_ACTIONS,
)
from ..exceptions import ExpenseSyncBaseException
from ..uow.unit_of_work import ExpenseSyncUnitOfWork

logger = logging.getLogger(__name__)


@dataclass
class ExpenseSyncSetupResult:
    """Результат инициализации инфраструктуры."""

    account_id: str
    mirror_customentity_id: str | None = None
    counterparty_attribute_id: str | None = None
    elements_created: int = 0
    elements_skipped: int = 0
    webhooks_created: int = 0
    webhooks_existing: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return (
            bool(self.mirror_customentity_id)
            and bool(self.counterparty_attribute_id)
            and not self.errors
        )


class ExpenseItemSetupService:
    """Создание и наполнение инфраструктуры синхронизации статей расходов."""

    def __init__(
        self,
        auth_service: MySkladAuthService,
        uow: ExpenseSyncUnitOfWork,
        expenseitem_service: ExpenseItemService,
        customentity_service: CustomEntityService,
        counterparty_service: CounterpartyService,
    ) -> None:
        self._auth_service = auth_service
        self._uow = uow
        self._expenseitem_service = expenseitem_service
        self._customentity_service = customentity_service
        self._counterparty_service = counterparty_service

    def _require_account_id(self) -> str:
        account_id = self._auth_service.get_account_id()
        if not account_id:
            raise ExpenseSyncBaseException(
                "AccountId не найден. Активируйте приложение через Vendor API"
            )
        return account_id

    async def initialize(self) -> ExpenseSyncSetupResult:
        """Создать/доинициализировать инфраструктуру для текущего аккаунта."""
        account_id = self._require_account_id()
        result = ExpenseSyncSetupResult(account_id=account_id)

        config = await self._uow.configs.get_by_account_id(account_id)
        mirror_id = config.mirror_customentity_id if config else None
        attribute_id = config.counterparty_attribute_id if config else None

        # 1. Справочник-зеркало
        if not mirror_id:
            dictionary = await self._customentity_service.create_dictionary(
                MIRROR_DICTIONARY_NAME
            )
            mirror_id = dictionary.id
            await self._uow.configs.upsert(
                account_id, mirror_customentity_id=mirror_id
            )
            await self._uow.commit()
            logger.info(
                "Создан справочник-зеркало статей расходов: account_id=%s, id=%s",
                account_id,
                mirror_id,
            )
        result.mirror_customentity_id = mirror_id

        # 2. Бэкафилл статей расходов в справочник + локальные соответствия
        created, skipped = await self._backfill_elements(account_id, mirror_id)
        result.elements_created = created
        result.elements_skipped = skipped
        await self._uow.commit()

        # 3. Доп. поле контрагента
        if not attribute_id:
            attribute = await self._counterparty_service.create_customentity_attribute(
                name=COUNTERPARTY_ATTRIBUTE_NAME,
                customentity_metadata_id=mirror_id,
            )
            attribute_id = attribute.get("id")
            await self._uow.configs.upsert(
                account_id, counterparty_attribute_id=attribute_id
            )
            await self._uow.commit()
            logger.info(
                "Создано доп. поле контрагента: account_id=%s, attribute_id=%s",
                account_id,
                attribute_id,
            )
        result.counterparty_attribute_id = attribute_id

        # 4. Вебхуки синхронизации
        await self._register_sync_webhooks(result)

        return result

    async def _backfill_elements(
        self, account_id: str, mirror_id: str
    ) -> tuple[int, int]:
        """Создать недостающие элементы справочника по текущим статьям расходов."""
        expense_items = await self._expenseitem_service.list_all()
        existing_mappings = await self._uow.mappings.list_by_account(account_id)
        mapped_ids = {m.expenseitem_id for m in existing_mappings}

        created = 0
        skipped = 0

        for item in expense_items:
            if item.id in mapped_ids:
                skipped += 1
                continue

            element = await self._customentity_service.create_element(
                metadata_id=mirror_id,
                name=item.name,
                description=item.description,
                code=item.code,
                # кросс-ссылка только на стороне зеркала, не трогаем expenseitem
                external_code=item.id,
            )
            await self._uow.mappings.add(account_id, item.id, element.id)
            created += 1

        logger.info(
            "Бэкафилл статей расходов: account_id=%s, создано=%d, пропущено=%d",
            account_id,
            created,
            skipped,
        )
        return created, skipped

    async def _register_sync_webhooks(self, result: ExpenseSyncSetupResult) -> None:
        """Зарегистрировать вебхуки для expenseitem и customentity."""
        webhook_url = settings.ms_webhook_url
        if not webhook_url:
            result.errors.append(
                "MS_WEBHOOK_URL не задан — вебхуки синхронизации не зарегистрированы"
            )
            logger.warning("MS_WEBHOOK_URL не задан, пропускаем регистрацию вебхуков")
            return

        # Локальный импорт во избежание циклической зависимости hooks <-> expense_sync.
        from ...hooks.services.moysklad_client import MoySkladClient

        client = MoySkladClient(self._auth_service)

        try:
            existing = await client.list_webhooks()
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            result.errors.append(f"Не удалось получить список вебхуков: {exc}")
            logger.warning("Не удалось получить список вебхуков: %s", exc)
            existing = []

        existing_keys = {
            (w.get("entityType"), w.get("action"), w.get("url")) for w in existing
        }

        # Вебхуки синхронизации справочника + вебхуки на создание исходящих
        # документов (для автопроставления статьи расходов).
        required: list[tuple[str, str]] = [
            (entity_type, action)
            for entity_type in (EXPENSEITEM_ENTITY_TYPE, CUSTOMENTITY_ENTITY_TYPE)
            for action in SYNC_WEBHOOK_ACTIONS
        ]
        required += [
            (entity_type, EXPENSE_PAYMENT_WEBHOOK_ACTION)
            for entity_type in EXPENSE_PAYMENT_ENTITY_TYPES
        ]

        for entity_type, action in required:
            if (entity_type, action, webhook_url) in existing_keys:
                result.webhooks_existing += 1
                continue
            try:
                await client.create_webhook(
                    entity_type=entity_type,
                    action=action,
                    url=webhook_url,
                )
                result.webhooks_created += 1
            except Exception as exc:  # pragma: no cover - сетевые ошибки
                msg = f"Не удалось создать вебхук {entity_type}/{action}: {exc}"
                result.errors.append(msg)
                logger.warning(msg)
