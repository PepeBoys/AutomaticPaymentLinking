"""Инфраструктура и настройки статей доходов/расходов в первичных документах.

Доп. поля «Статья доходов» (заказ покупателя, счёт покупателю, отгрузка) и
«Статья расходов» (заказ поставщику, счёт поставщика, приёмка) ссылаются на
те же справочники, что и доп. поля контрагента: «Статьи доходов» (income_sync)
и справочник-зеркало статей расходов (expense_sync). Поэтому значение из
контрагента можно скопировать в документ как есть.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from ...customentity.attributes import (
    build_customentity_attribute_payload,
    find_customentity_attribute,
)
from ...expense_sync.uow.unit_of_work import ExpenseSyncUnitOfWork
from ...income_sync.uow.unit_of_work import IncomeSyncUnitOfWork
from ...ms_auth.services.auth_service import MySkladAuthService
from ..constants import (
    DOCUMENT_LABELS,
    EXPENSE_ATTRIBUTE_NAME,
    EXPENSE_DOCUMENT_TYPES,
    INCOME_ATTRIBUTE_NAME,
    INCOME_DOCUMENT_TYPES,
    MODE_OFF,
    MODES,
)
from ..exceptions import DocumentItemsAPIError, DocumentItemsBaseException
from ..repository import DocumentItemsConfigRepository, attribute_field
from .client import DocumentItemsClient

logger = logging.getLogger(__name__)


@dataclass
class SideStatus:
    """Состояние одной стороны (доходы или расходы)."""

    dictionary_ready: bool
    attributes_ready: bool
    mode: str


@dataclass
class DocumentItemsSetupResult:
    created: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class DocumentItemsSettingsService:
    def __init__(self, auth_service: MySkladAuthService, session) -> None:
        self._auth_service = auth_service
        self._configs = DocumentItemsConfigRepository(session)
        self._income = IncomeSyncUnitOfWork(session)
        self._expense = ExpenseSyncUnitOfWork(session)
        self._client = DocumentItemsClient(auth_service)

    def _require_account_id(self) -> str:
        account_id = self._auth_service.get_account_id()
        if not account_id:
            raise DocumentItemsBaseException(
                "AccountId не найден. Активируйте приложение через Vendor API"
            )
        return account_id

    async def _dictionaries(self, account_id: str) -> tuple[Optional[str], Optional[str]]:
        """id справочников статей доходов и расходов (если фичи инициализированы)."""
        income = await self._income.configs.get_by_account_id(account_id)
        expense = await self._expense.configs.get_by_account_id(account_id)
        return (
            income.dictionary_id if income and income.is_initialized else None,
            expense.mirror_customentity_id if expense and expense.is_initialized else None,
        )

    async def get_status(self) -> dict:
        account_id = self._require_account_id()
        income_dict, expense_dict = await self._dictionaries(account_id)
        config = await self._configs.get(account_id)

        def side(types: tuple, dictionary_id: Optional[str], mode_attr: str) -> SideStatus:
            ready = bool(config) and all(getattr(config, attribute_field(t)) for t in types)
            return SideStatus(
                dictionary_ready=bool(dictionary_id),
                attributes_ready=ready,
                mode=getattr(config, mode_attr) if config else MODE_OFF,
            )

        return {
            "income": side(INCOME_DOCUMENT_TYPES, income_dict, "income_mode").__dict__,
            "expense": side(EXPENSE_DOCUMENT_TYPES, expense_dict, "expense_mode").__dict__,
        }

    async def initialize(self) -> DocumentItemsSetupResult:
        """Создать недостающие доп. поля в документах (идемпотентно)."""
        account_id = self._require_account_id()
        income_dict, expense_dict = await self._dictionaries(account_id)
        result = DocumentItemsSetupResult()

        sides = (
            (INCOME_DOCUMENT_TYPES, income_dict, INCOME_ATTRIBUTE_NAME, "статьи доходов"),
            (EXPENSE_DOCUMENT_TYPES, expense_dict, EXPENSE_ATTRIBUTE_NAME, "статьи расходов"),
        )
        for types, dictionary_id, attribute_name, label in sides:
            if not dictionary_id:
                result.errors.append(f"Сначала инициализируйте справочник {label}")
                continue
            for document_type in types:
                await self._ensure_attribute(
                    account_id, document_type, attribute_name, dictionary_id, result
                )

        await self._configs.commit()
        logger.info(
            "Инициализация статей в документах: account_id=%s, created=%s, errors=%s",
            account_id,
            result.created,
            result.errors,
        )
        return result

    async def _ensure_attribute(
        self,
        account_id: str,
        document_type: str,
        attribute_name: str,
        dictionary_id: str,
        result: DocumentItemsSetupResult,
    ) -> None:
        config = await self._configs.get_or_create(account_id)
        current_id = getattr(config, attribute_field(document_type))
        label = DOCUMENT_LABELS[document_type]

        try:
            attributes = await self._client.list_attributes(document_type)
            if current_id and any(a.get("id") == current_id for a in attributes):
                return

            existing = find_customentity_attribute(attributes, attribute_name)
            if existing is None:
                payload = build_customentity_attribute_payload(
                    self._client.base_url(), attribute_name, dictionary_id
                )
                attribute_id = (await self._client.create_attribute(document_type, payload))["id"]
                result.created.append(document_type)
            elif existing.get("customentity_id") == dictionary_id:
                attribute_id = existing["id"]  # наше поле — переиспользуем
            else:
                result.errors.append(
                    f"Доп. поле {label} «{attribute_name}» уже существует и ссылается на "
                    "другой справочник. Удалите или переименуйте его в МойСклад и повторите."
                )
                return
        except DocumentItemsAPIError as exc:
            result.errors.append(f"Не удалось создать доп. поле {label}: {exc.message} {exc.details}")
            return

        await self._configs.set_attribute(account_id, document_type, attribute_id)

    async def set_modes(self, income_mode: Optional[str], expense_mode: Optional[str]) -> dict:
        """Сменить режимы. Включить сторону можно, только если её доп. поля созданы."""
        account_id = self._require_account_id()
        status = await self.get_status()
        config = await self._configs.get_or_create(account_id)

        for side, mode, attr in (
            ("income", income_mode, "income_mode"),
            ("expense", expense_mode, "expense_mode"),
        ):
            if mode is None:
                continue
            if mode not in MODES:
                raise DocumentItemsBaseException(f"Неизвестный режим: {mode}")
            if mode != MODE_OFF and not status[side]["attributes_ready"]:
                return {
                    "status": "warning",
                    "message": "Сначала создайте доп. поля в документах (кнопка «Создать поля»)",
                }
            setattr(config, attr, mode)

        await self._configs.commit()
        return {"status": "ok", **(await self.get_status())}
