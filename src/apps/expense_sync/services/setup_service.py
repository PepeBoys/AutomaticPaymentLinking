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

        # 3. Доп. поле контрагента (adopt-or-create + защита от коллизии имени)
        if not attribute_id:
            existing_attr = await self._counterparty_service.find_customentity_attribute_by_name(
                COUNTERPARTY_ATTRIBUTE_NAME
            )

            if existing_attr is None:
                attribute = await self._counterparty_service.create_customentity_attribute(
                    name=COUNTERPARTY_ATTRIBUTE_NAME,
                    customentity_metadata_id=mirror_id,
                )
                attribute_id = attribute.get("id")
                logger.info(
                    "Создано доп. поле контрагента: account_id=%s, attribute_id=%s",
                    account_id,
                    attribute_id,
                )
            elif existing_attr.get("customentity_id") == mirror_id:
                # Наше же поле — идемпотентный повторный запуск, переиспользуем.
                attribute_id = existing_attr.get("id")
                logger.info(
                    "Доп. поле контрагента уже существует, переиспользуем: %s",
                    attribute_id,
                )
            else:
                msg = (
                    f"Доп. поле контрагента «{COUNTERPARTY_ATTRIBUTE_NAME}» уже существует "
                    f"(id={existing_attr.get('id')}) и ссылается на другой справочник "
                    f"({existing_attr.get('customentity_id')}), а не на зеркало ({mirror_id}). "
                    "Удалите или переименуйте это поле в МойСклад и повторите инициализацию."
                )
                result.errors.append(msg)
                logger.warning(msg)

            if attribute_id:
                await self._uow.configs.upsert(
                    account_id, counterparty_attribute_id=attribute_id
                )
                await self._uow.commit()

        result.counterparty_attribute_id = attribute_id

        # 4. Вебхуки синхронизации
        await self._register_sync_webhooks(result)

        # 5. Автопроставление включаем по умолчанию после успешной
        # инициализации/обновления справочника (справочник + доп. поле на месте).
        if mirror_id and attribute_id:
            await self._uow.configs.upsert(account_id, enabled=True)
            await self._uow.commit()

        return result

    @staticmethod
    def _element_content_diff(item, element) -> dict:
        """Поля статьи, которые нужно записать в элемент зеркала (Статья → зеркало).

        None в источнике трактуем как «не синхронизировать это поле» —
        симметрично логике вебхуков, чтобы не плодить пустые PUT и эхо-петли.
        """
        diff: dict = {}
        for key, src, dst in (
            ("name", item.name, element.name),
            ("description", item.description, element.description),
            ("code", item.code, element.code),
        ):
            if src is None:
                continue
            if dst != src:
                diff[key] = src
        return diff

    async def _backfill_elements(
        self, account_id: str, mirror_id: str
    ) -> tuple[int, int]:
        """Заполнить справочник-зеркало по текущим статьям расходов.

        Источник истины — фактическое содержимое справочника в МС (а не
        локальные маппинги): так на повторной инициализации/обновлении
        восстанавливаются элементы, удалённые в МС вручную (в т.ч. пока
        приложение было снято), и чинятся «осиротевшие» маппинги.
        """
        expense_items = await self._expenseitem_service.list_all()
        existing_elements = await self._customentity_service.list_elements(mirror_id)
        # external_code элемента = id статьи расходов (кросс-ссылка на стороне зеркала).
        element_by_item_id = {
            el.external_code: el for el in existing_elements if el.external_code
        }
        existing_mappings = await self._uow.mappings.list_by_account(account_id)
        mapping_by_item_id = {m.expenseitem_id: m for m in existing_mappings}

        created = 0
        skipped = 0
        updated = 0

        for item in expense_items:
            element = element_by_item_id.get(item.id)

            if element is not None:
                # Элемент в справочнике есть — приводим маппинг в соответствие.
                mapping = mapping_by_item_id.get(item.id)
                if mapping is None:
                    await self._uow.mappings.add(account_id, item.id, element.id)
                elif mapping.customentity_element_id != element.id:
                    await self._uow.mappings.delete_by_expenseitem(account_id, item.id)
                    await self._uow.mappings.add(account_id, item.id, element.id)
                # Содержимое пары разошлось — подтягиваем элемент к статье
                # (Статья расходов — источник истины для существующих пар).
                content = self._element_content_diff(item, element)
                if content:
                    await self._customentity_service.update_element(
                        mirror_id, element.id, **content
                    )
                    updated += 1
                skipped += 1
                continue

            # Элемента в справочнике нет — снимаем устаревший маппинг (если есть)
            # и создаём элемент заново.
            if item.id in mapping_by_item_id:
                await self._uow.mappings.delete_by_expenseitem(account_id, item.id)

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

        # Обратный проход: элементы зеркала без живой статьи (external_code
        # устарел или отсутствует) — зеркало «опережает». Восстанавливаем статью
        # из элемента, чиним кросс-ссылку и локальное соответствие. Симметрично
        # живой синхронизации customentity→expenseitem.
        item_ids = {item.id for item in expense_items}
        restored = 0
        for element in existing_elements:
            if element.external_code and element.external_code in item_ids:
                continue  # сопоставлен с существующей статьёй — обработан выше

            new_item = await self._expenseitem_service.create(
                name=element.name,
                description=element.description,
                code=element.code,
            )
            # Восстанавливаем кросс-ссылку на стороне зеркала и соответствие.
            await self._customentity_service.update_element(
                mirror_id, element.id, external_code=new_item.id
            )
            await self._uow.mappings.delete_by_element(account_id, element.id)
            await self._uow.mappings.add(account_id, new_item.id, element.id)
            # Коммитим сразу: создание статьи уже отправило вебхук expenseitem
            # CREATE — соответствие должно быть в БД до его обработки, иначе
            # эхо-обработчик создаст дублирующий элемент зеркала.
            await self._uow.commit()
            restored += 1

        logger.info(
            "Бэкафилл статей расходов: account_id=%s, создано=%d, пропущено=%d, "
            "обновлено=%d, восстановлено статей из зеркала=%d",
            account_id,
            created,
            skipped,
            updated,
            restored,
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
        from ...hooks.services.shared_webhooks import ensure_webhooks_enabled

        client = MoySkladClient(self._auth_service)

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

        # Общие с автопривязкой вебхуки (paymentout/cashout CREATE) могли быть
        # выключены ею — включаем обратно, а не считаем «уже существующими».
        ensured = await ensure_webhooks_enabled(client, webhook_url, required)
        result.webhooks_created += ensured.created
        result.webhooks_existing += ensured.existing + ensured.enabled
        result.errors.extend(ensured.errors)
