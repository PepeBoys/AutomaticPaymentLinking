"""Управление настройками фичи синхронизации статей расходов."""

import logging

from ...counterparty.exceptions import CounterpartyAPIError
from ...counterparty.services.counterparty_service import CounterpartyService
from ...customentity.exceptions import (
    CustomEntityAPIError,
    CustomEntityNotFoundError,
)
from ...customentity.services.customentity_service import CustomEntityService
from ...expenseitem.services.expenseitem_service import ExpenseItemService
from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import ExpenseSyncBaseException
from ..uow.unit_of_work import ExpenseSyncUnitOfWork

logger = logging.getLogger(__name__)


class ExpenseSyncService:
    """Статус и переключение фичи автопроставления статьи расходов."""

    def __init__(
        self,
        auth_service: MySkladAuthService,
        uow: ExpenseSyncUnitOfWork,
        customentity_service: CustomEntityService,
        counterparty_service: CounterpartyService,
        expenseitem_service: ExpenseItemService,
    ) -> None:
        self._auth_service = auth_service
        self._uow = uow
        self._customentity_service = customentity_service
        self._counterparty_service = counterparty_service
        self._expenseitem_service = expenseitem_service

    # Тексты диагностики для UI: почему инфраструктура считается неготовой.
    _DIAGNOSTIC_MESSAGES = {
        "mirror_missing": (
            "Справочник-зеркало статей расходов не найден в МойСклад "
            "(вместе с ним удалено и доп. поле контрагента). "
            "Требуется повторная инициализация."
        ),
        "attribute_missing": (
            "Доп. поле контрагента не найдено в МойСклад. Справочник-зеркало "
            "найден, но мог рассинхронизироваться со «Статьями расходов» — "
            "требуется повторная инициализация."
        ),
    }

    @classmethod
    def _uninitialized_status(cls, diagnostic: str = "none") -> dict:
        return {
            "enabled": False,
            "initialized": False,
            "mirror_customentity_id": None,
            "counterparty_attribute_id": None,
            "mappings_count": 0,
            "diagnostic": diagnostic,
            "message": cls._DIAGNOSTIC_MESSAGES.get(diagnostic),
        }

    async def _mirror_exists(self, mirror_id: str) -> bool:
        """Жив ли справочник-зеркало в МойСклад.

        404 — справочник удалён (надёжный сигнал). При сетевой/прочей ошибке
        НЕ трогаем БД и считаем инфраструктуру существующей, чтобы транзиентный
        сбой не уничтожил конфиг.
        """
        try:
            await self._customentity_service.get_metadata(mirror_id)
            return True
        except CustomEntityNotFoundError:
            return False
        except CustomEntityAPIError as exc:
            logger.warning(
                "Не удалось проверить справочник-зеркало %s, считаем существующим: %s",
                mirror_id,
                exc,
            )
            return True

    async def _attribute_exists(self, attribute_id: str) -> bool:
        """Живо ли доп. поле контрагента в МойСклад.

        Семантика и обработка ошибок — как у :meth:`_mirror_exists`: при
        транзиентном сбое считаем поле существующим, чтобы не уничтожить конфиг.
        """
        try:
            return await self._counterparty_service.attribute_exists(attribute_id)
        except CounterpartyAPIError as exc:
            logger.warning(
                "Не удалось проверить доп. поле контрагента %s, считаем существующим: %s",
                attribute_id,
                exc,
            )
            return True

    async def _reset_stale_config(self, account_id: str) -> None:
        """Сбросить устаревшие настройки и маппинги удалённой инфраструктуры."""
        deleted = await self._uow.mappings.delete_all_by_account(account_id)
        await self._uow.configs.delete_by_account_id(account_id)
        await self._uow.commit()
        logger.info(
            "Сброшен устаревший конфиг expense_sync (справочник удалён в МС): "
            "account_id=%s, удалено маппингов=%d",
            account_id,
            deleted,
        )

    async def _clear_stale_attribute(self, account_id: str) -> None:
        """Сбросить ссылку на удалённое доп. поле (справочник при этом цел).

        Маппинги и сам справочник сохраняем — повторная инициализация
        пересоздаст доп. поле на существующем справочнике без дублей.
        """
        await self._uow.configs.clear_counterparty_attribute(account_id)
        await self._uow.commit()
        logger.info(
            "Сброшена ссылка на доп. поле expense_sync (поле удалено в МС, "
            "справочник цел): account_id=%s",
            account_id,
        )

    def _require_account_id(self) -> str:
        account_id = self._auth_service.get_account_id()
        if not account_id:
            raise ExpenseSyncBaseException(
                "AccountId не найден. Активируйте приложение через Vendor API"
            )
        return account_id

    async def get_status(self) -> dict:
        """Текущее состояние фичи для аккаунта."""
        account_id = self._require_account_id()
        config = await self._uow.configs.get_by_account_id(account_id)

        if config is None:
            return self._uninitialized_status()

        # Самовосстановление: если справочник-зеркало удалён в МойСклад
        # (например, пользователь удалил его вручную, пока приложение было
        # снято), сохранённые ID — «призрачные». Чистим конфиг и маппинги,
        # чтобы UI предложил инициализацию заново, а не «Обновить» по
        # несуществующему справочнику.
        if config.mirror_customentity_id and not await self._mirror_exists(
            config.mirror_customentity_id
        ):
            await self._reset_stale_config(account_id)
            return self._uninitialized_status("mirror_missing")

        # Справочник цел, но удалено только доп. поле контрагента — сбрасываем
        # ссылку на поле (маппинги и справочник сохраняем), чтобы повторная
        # инициализация пересоздала поле без дубля справочника.
        if config.counterparty_attribute_id and not await self._attribute_exists(
            config.counterparty_attribute_id
        ):
            await self._clear_stale_attribute(account_id)
            return self._uninitialized_status("attribute_missing")

        # Конфиг есть и зеркало живо, но ссылки на доп. поле нет (поле было
        # сброшено на предыдущем опросе или инициализация не завершилась).
        # Сохраняем диагностику между перезагрузками — UI продолжает показывать
        # причину, пока пользователь не выполнит повторную инициализацию.
        if not config.is_initialized:
            diagnostic = (
                "attribute_missing" if config.mirror_customentity_id else "none"
            )
            return self._uninitialized_status(diagnostic)

        mappings = await self._uow.mappings.list_by_account(account_id)
        return {
            "enabled": config.enabled,
            "initialized": config.is_initialized,
            "mirror_customentity_id": config.mirror_customentity_id,
            "counterparty_attribute_id": config.counterparty_attribute_id,
            "mappings_count": len(mappings),
            "diagnostic": "ok",
            "message": None,
        }

    async def set_enabled(self, enabled: bool) -> dict:
        """Включить/выключить автопроставление статьи расходов."""
        account_id = self._require_account_id()
        config = await self._uow.configs.get_by_account_id(account_id)

        if enabled and (config is None or not config.is_initialized):
            return {
                "status": "warning",
                "enabled": False,
                "message": (
                    "Инфраструктура не инициализирована. Сначала выполните "
                    "инициализацию справочника статей расходов."
                ),
            }

        await self._uow.configs.upsert(account_id, enabled=enabled)
        await self._uow.commit()

        logger.info(
            "Фича статьи расходов переключена: account_id=%s, enabled=%s",
            account_id,
            enabled,
        )
        return {"status": "ok", "enabled": enabled}

    @staticmethod
    def _norm(value: str | None) -> str:
        """Нормализация поля для сравнения: None и пустая строка эквивалентны."""
        return (value or "").strip()

    @classmethod
    def _changed_fields(cls, item, element) -> list[str]:
        """Поля, разошедшиеся между статьёй расходов и элементом зеркала."""
        fields = []
        if cls._norm(item.name) != cls._norm(element.name):
            fields.append("name")
        if cls._norm(item.code) != cls._norm(element.code):
            fields.append("code")
        if cls._norm(item.description) != cls._norm(element.description):
            fields.append("description")
        return fields

    @staticmethod
    def _empty_diff(status: str) -> dict:
        return {
            "status": status,
            "in_sync": status == "ok",
            "source_count": 0,
            "mirror_count": 0,
            "missing_in_mirror": [],
            "orphan_in_mirror": [],
            "changed": [],
            "extra_in_mirror": [],
            "duplicate_in_mirror": [],
        }

    async def compute_diff(self) -> dict:
        """Сравнить справочник-зеркало со справочником «Статьи расходов».

        Кросс-ссылка: ``element.external_code == expenseitem.id``. Возвращает,
        чем зеркало отстаёт (статья есть, элемента нет), чем опережает (элемент
        есть, статья удалена) и какие элементы рассинхронизированы по полям.
        Привести зеркало к актуальному состоянию можно повторной инициализацией
        (кнопка «Обновить справочник»).
        """
        account_id = self._require_account_id()
        config = await self._uow.configs.get_by_account_id(account_id)
        if config is None or not config.mirror_customentity_id:
            return self._empty_diff("uninitialized")

        mirror_id = config.mirror_customentity_id
        try:
            elements = await self._customentity_service.list_elements(mirror_id)
        except CustomEntityNotFoundError:
            # Зеркало удалено в МС — статус сам это вылечит на ближайшем опросе.
            return self._empty_diff("uninitialized")

        items = await self._expenseitem_service.list_all()
        items_by_id = {it.id: it for it in items}

        # Группируем элементы по external_code — чтобы НЕ схлопывать дубликаты
        # (несколько элементов с одной кросс-ссылкой). Элементы без external_code
        # отправляются в extra_in_mirror.
        elements_by_ext: dict[str, list] = {}
        extra_in_mirror: list[dict] = []
        for el in elements:
            if el.external_code:
                elements_by_ext.setdefault(el.external_code, []).append(el)
            else:
                extra_in_mirror.append({"element_id": el.id, "mirror_name": el.name})

        missing_in_mirror: list[dict] = []
        changed: list[dict] = []
        duplicate_in_mirror: list[dict] = []
        for item in items:
            group = elements_by_ext.get(item.id)
            if not group:
                missing_in_mirror.append(
                    {"expenseitem_id": item.id, "source_name": item.name}
                )
                continue

            element = group[0]  # канонический элемент пары
            fields = self._changed_fields(item, element)
            if fields:
                changed.append(
                    {
                        "expenseitem_id": item.id,
                        "element_id": element.id,
                        "source_name": item.name,
                        "mirror_name": element.name,
                        "changed_fields": fields,
                    }
                )
            # Лишние копии с тем же external_code — дубликаты (зеркало раздуто).
            for dup in group[1:]:
                duplicate_in_mirror.append(
                    {
                        "expenseitem_id": item.id,
                        "element_id": dup.id,
                        "source_name": item.name,
                        "mirror_name": dup.name,
                    }
                )

        # external_code указывает на несуществующую статью → зеркало опережает.
        # Все копии такой группы считаем сиротами.
        orphan_in_mirror = [
            {"element_id": el.id, "mirror_name": el.name}
            for ext, group in elements_by_ext.items()
            if ext not in items_by_id
            for el in group
        ]

        in_sync = not (
            missing_in_mirror
            or orphan_in_mirror
            or changed
            or extra_in_mirror
            or duplicate_in_mirror
        )
        return {
            "status": "ok",
            "in_sync": in_sync,
            "source_count": len(items),
            "mirror_count": len(elements),
            "missing_in_mirror": missing_in_mirror,
            "orphan_in_mirror": orphan_in_mirror,
            "changed": changed,
            "extra_in_mirror": extra_in_mirror,
            "duplicate_in_mirror": duplicate_in_mirror,
        }
