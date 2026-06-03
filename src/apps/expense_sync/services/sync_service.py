"""Двусторонняя синхронизация статей расходов и справочника-зеркала.

Обрабатывает вебхуки МойСклад:
- expenseitem CREATE/UPDATE/DELETE → применяет изменения к элементу
  справочника-зеркала;
- customentity CREATE/UPDATE/DELETE → применяет изменения к парной статье
  расходов (только для элементов нашего справочника-зеркала).

Защита от эхо-петли:
- для CREATE/UPDATE используется compare-before-write: если значения уже
  совпадают, запись не выполняется (наш собственный апдейт-эхо игнорируется);
- для DELETE сначала удаляется локальное соответствие, затем близнец в МС —
  обратный вебхук уже не находит соответствие и завершается no-op.
"""

import logging
from typing import Optional

from ...counterparty.exceptions import CounterpartyNotFoundError
from ...counterparty.services.counterparty_service import CounterpartyService
from ...customentity.exceptions import CustomEntityNotFoundError
from ...customentity.services.customentity_service import CustomEntityService
from ...expenseitem.exceptions import ExpenseItemNotFoundError
from ...expenseitem.services.expenseitem_service import ExpenseItemService
from ...ms_auth.services.auth_service import MySkladAuthService
from ..uow.unit_of_work import ExpenseSyncUnitOfWork

logger = logging.getLogger(__name__)


def _extract_id_from_href(href: str) -> str:
    """Извлечь id сущности из href (последний сегмент пути)."""
    return href.rstrip("/").split("/")[-1]


def _content_diff(source_fields: dict, target_fields: dict) -> dict:
    """Вернуть поля, которые нужно записать в близнеца.

    Поле попадает в результат, только если значение источника не None и
    отличается от значения цели. None в источнике трактуется как «не
    синхронизировать это поле» — это исключает бесконечную петлю на полях,
    которые мы не умеем очищать частичным PUT.
    """
    diff: dict = {}
    for key, src_value in source_fields.items():
        if src_value is None:
            continue
        if target_fields.get(key) != src_value:
            diff[key] = src_value
    return diff


class ExpenseSyncHandler:
    """Применяет события вебхуков к парной сущности (статья ↔ зеркало)."""

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

    async def _get_mirror_id(self, account_id: str) -> Optional[str]:
        config = await self._uow.configs.get_by_account_id(account_id)
        if not config or not config.mirror_customentity_id:
            logger.debug(
                "Синхронизация статей расходов не настроена для account_id=%s",
                account_id,
            )
            return None
        return config.mirror_customentity_id

    # ===== expenseitem → customentity (зеркало) =====

    async def handle_expenseitem_event(
        self, account_id: str, action: str, href: str
    ) -> None:
        mirror_id = await self._get_mirror_id(account_id)
        if not mirror_id:
            return

        item_id = _extract_id_from_href(href)

        if action == "DELETE":
            await self._delete_mirror_for_expenseitem(account_id, mirror_id, item_id)
            return

        try:
            item = await self._expenseitem_service.get_by_id(item_id)
        except ExpenseItemNotFoundError:
            logger.warning("Статья расходов %s не найдена при синхронизации", item_id)
            return

        mapping = await self._uow.mappings.get_by_expenseitem(account_id, item_id)
        if mapping:
            await self._update_mirror_element_if_changed(
                mirror_id, mapping.customentity_element_id, item
            )
        else:
            await self._create_mirror_element(account_id, mirror_id, item)

    async def _create_mirror_element(self, account_id: str, mirror_id: str, item) -> None:
        element = await self._customentity_service.create_element(
            metadata_id=mirror_id,
            name=item.name,
            description=item.description,
            code=item.code,
            external_code=item.id,  # кросс-ссылка только на стороне зеркала
        )
        await self._uow.mappings.add(account_id, item.id, element.id)
        await self._uow.commit()
        logger.info(
            "Создан элемент-зеркало %s для статьи расходов %s", element.id, item.id
        )

    async def _update_mirror_element_if_changed(
        self, mirror_id: str, element_id: str, item
    ) -> None:
        try:
            element = await self._customentity_service.get_element(mirror_id, element_id)
        except CustomEntityNotFoundError:
            logger.warning("Элемент-зеркало %s не найден при синхронизации", element_id)
            return

        diff = _content_diff(
            {"name": item.name, "description": item.description, "code": item.code},
            {
                "name": element.name,
                "description": element.description,
                "code": element.code,
            },
        )
        if not diff:
            logger.debug("Элемент-зеркало %s уже актуален, пропуск", element_id)
            return

        await self._customentity_service.update_element(mirror_id, element_id, **diff)
        logger.info(
            "Обновлён элемент-зеркало %s из статьи расходов (поля: %s)",
            element_id,
            list(diff.keys()),
        )

    async def _delete_mirror_for_expenseitem(
        self, account_id: str, mirror_id: str, item_id: str
    ) -> None:
        mapping = await self._uow.mappings.get_by_expenseitem(account_id, item_id)
        if not mapping:
            logger.debug("Нет соответствия для удалённой статьи %s, пропуск", item_id)
            return

        element_id = mapping.customentity_element_id
        # Удаляем соответствие ДО удаления близнеца — обратный вебхук не найдёт
        # соответствие и завершится no-op (защита от петли).
        await self._uow.mappings.delete_by_expenseitem(account_id, item_id)
        await self._uow.commit()

        await self._customentity_service.delete_element(mirror_id, element_id)
        logger.info(
            "Удалён элемент-зеркало %s (статья расходов %s удалена)",
            element_id,
            item_id,
        )

    # ===== customentity (зеркало) → expenseitem =====

    async def handle_customentity_event(
        self, account_id: str, action: str, href: str
    ) -> None:
        mirror_id = await self._get_mirror_id(account_id)
        if not mirror_id:
            return

        # Вебхук customentity глобален для всех справочников — реагируем только
        # на элементы нашего справочника-зеркала.
        if f"/customentity/{mirror_id}/" not in href:
            logger.debug("Событие customentity вне зеркала, пропуск: %s", href)
            return

        element_id = _extract_id_from_href(href)

        if action == "DELETE":
            await self._delete_expenseitem_for_element(account_id, element_id)
            return

        try:
            element = await self._customentity_service.get_element(mirror_id, element_id)
        except CustomEntityNotFoundError:
            logger.warning("Элемент-зеркало %s не найден при синхронизации", element_id)
            return

        mapping = await self._uow.mappings.get_by_element(account_id, element_id)
        if mapping:
            await self._update_expenseitem_if_changed(mapping.expenseitem_id, element)
        else:
            await self._create_expenseitem_from_element(account_id, element)

    async def _create_expenseitem_from_element(self, account_id: str, element) -> None:
        item = await self._expenseitem_service.create(
            name=element.name,
            description=element.description,
            code=element.code,
            # externalCode статьи не трогаем — соответствие держим локально
        )
        await self._uow.mappings.add(account_id, item.id, element.id)
        await self._uow.commit()
        logger.info(
            "Создана статья расходов %s из элемента-зеркала %s", item.id, element.id
        )

    async def _update_expenseitem_if_changed(self, expenseitem_id: str, element) -> None:
        try:
            item = await self._expenseitem_service.get_by_id(expenseitem_id)
        except ExpenseItemNotFoundError:
            logger.warning(
                "Статья расходов %s не найдена при синхронизации", expenseitem_id
            )
            return

        diff = _content_diff(
            {
                "name": element.name,
                "description": element.description,
                "code": element.code,
            },
            {"name": item.name, "description": item.description, "code": item.code},
        )
        if not diff:
            logger.debug("Статья расходов %s уже актуальна, пропуск", expenseitem_id)
            return

        await self._expenseitem_service.update(expenseitem_id, **diff)
        logger.info(
            "Обновлена статья расходов %s из элемента-зеркала (поля: %s)",
            expenseitem_id,
            list(diff.keys()),
        )

    async def _delete_expenseitem_for_element(
        self, account_id: str, element_id: str
    ) -> None:
        mapping = await self._uow.mappings.get_by_element(account_id, element_id)
        if not mapping:
            logger.debug(
                "Нет соответствия для удалённого элемента %s, пропуск", element_id
            )
            return

        expenseitem_id = mapping.expenseitem_id
        await self._uow.mappings.delete_by_element(account_id, element_id)
        await self._uow.commit()

        await self._expenseitem_service.delete(expenseitem_id)
        logger.info(
            "Удалена статья расходов %s (элемент-зеркало %s удалён)",
            expenseitem_id,
            element_id,
        )

    # ===== Автопроставление статьи расходов в исходящий платёж/ордер =====

    async def apply_expense_item_to_payment(
        self, account_id: str, href: str, payment_service
    ) -> None:
        """Проставить статью расходов в paymentout/cashout по контрагенту.

        Цепочка: платёж → контрагент → доп. поле (ссылка на элемент зеркала)
        → локальное соответствие → статья расходов → update_expense_item.

        Не бросает исключений: любые сбои логируются и не прерывают остальную
        обработку вебхука (graceful degradation, как при переносе проекта).
        """
        config = await self._uow.configs.get_by_account_id(account_id)
        if not config or not config.enabled or not config.counterparty_attribute_id:
            return

        try:
            payment = await payment_service.get_by_href(href)
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            logger.warning("Не удалось получить платёж для статьи расходов: %s", exc)
            return

        if not payment.agent_id:
            logger.info("У платежа %s нет контрагента, пропуск статьи расходов", payment.id)
            return

        try:
            counterparty = await self._counterparty_service.get_by_id(payment.agent_id)
        except CounterpartyNotFoundError:
            logger.warning("Контрагент %s не найден для статьи расходов", payment.agent_id)
            return
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            logger.warning("Не удалось получить контрагента %s: %s", payment.agent_id, exc)
            return

        value = counterparty.get_attribute_value(config.counterparty_attribute_id)
        element_href = self._extract_element_href(value)
        if not element_href:
            logger.info(
                "У контрагента %s не заполнено доп. поле статьи расходов, пропуск",
                payment.agent_id,
            )
            return

        element_id = _extract_id_from_href(element_href)
        mapping = await self._uow.mappings.get_by_element(account_id, element_id)
        if not mapping:
            logger.warning(
                "Нет соответствия для элемента %s (контрагент %s) — статья не проставлена",
                element_id,
                payment.agent_id,
            )
            return

        try:
            item = await self._expenseitem_service.get_by_id(mapping.expenseitem_id)
        except ExpenseItemNotFoundError:
            logger.warning(
                "Статья расходов %s не найдена для проставления", mapping.expenseitem_id
            )
            return

        if payment.expense_item_meta_href == item.meta_href:
            logger.debug(
                "Статья расходов уже проставлена в платёж %s, пропуск", payment.id
            )
            return

        try:
            await payment_service.update_expense_item(payment.id, item.meta_href)
            logger.info(
                "✓ Статья расходов '%s' проставлена в платёж %s (контрагент %s)",
                item.name,
                payment.id,
                payment.agent_id,
            )
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            logger.warning(
                "Не удалось проставить статью расходов в платёж %s: %s", payment.id, exc
            )

    @staticmethod
    def _extract_element_href(value) -> Optional[str]:
        """Извлечь href элемента справочника из значения доп. поля типа справочник.

        Значение доп. поля типа «справочник» — объект {meta: {href}, name}.
        """
        if isinstance(value, dict):
            meta = value.get("meta")
            if isinstance(meta, dict):
                return meta.get("href")
        return None
