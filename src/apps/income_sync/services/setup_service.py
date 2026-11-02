"""Инициализация инфраструктуры автопроставления статьи доходов.

Создаёт пользовательский справочник «Статьи доходов», доп. поля контрагента,
входящего платежа и приходного ордера, ссылающиеся на него, и регистрирует
вебхуки на создание входящих платежей/ордеров.

Операция идемпотентна: повторный запуск переиспользует уже созданные
справочник и доп. поля и не создаёт дубликатов.
"""

import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional

from src.core.config import settings

from ...cashin.services.cashin_service import CashInService
from ...counterparty.exceptions import CounterpartyAPIError
from ...counterparty.services.counterparty_service import CounterpartyService
from ...customentity.services.customentity_service import CustomEntityService
from ...ms_auth.services.auth_service import MySkladAuthService
from ...payment_base.exceptions import PaymentAPIError
from ...paymentin.services.paymentin_service import PaymentInService
from ..constants import (
    COUNTERPARTY_ATTRIBUTE_NAME,
    DICTIONARY_NAME,
    INCOME_PAYMENT_ENTITY_TYPES,
    INCOME_PAYMENT_WEBHOOK_ACTION,
    PAYMENT_ATTRIBUTE_NAME,
)
from ..exceptions import IncomeSyncBaseException
from ..uow.unit_of_work import IncomeSyncUnitOfWork

logger = logging.getLogger(__name__)


@dataclass
class IncomeSyncSetupResult:
    """Результат инициализации инфраструктуры."""

    account_id: str
    dictionary_id: Optional[str] = None
    counterparty_attribute_id: Optional[str] = None
    paymentin_attribute_id: Optional[str] = None
    cashin_attribute_id: Optional[str] = None
    webhooks_created: int = 0
    webhooks_existing: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return (
            bool(self.dictionary_id)
            and bool(self.counterparty_attribute_id)
            and bool(self.paymentin_attribute_id)
            and bool(self.cashin_attribute_id)
            and not self.errors
        )


class IncomeItemSetupService:
    """Создание инфраструктуры автопроставления статьи доходов."""

    def __init__(
        self,
        auth_service: MySkladAuthService,
        uow: IncomeSyncUnitOfWork,
        customentity_service: CustomEntityService,
        counterparty_service: CounterpartyService,
        paymentin_service: PaymentInService,
        cashin_service: CashInService,
    ) -> None:
        self._auth_service = auth_service
        self._uow = uow
        self._customentity_service = customentity_service
        self._counterparty_service = counterparty_service
        self._payment_services = {
            "paymentin": paymentin_service,
            "cashin": cashin_service,
        }

    def _require_account_id(self) -> str:
        account_id = self._auth_service.get_account_id()
        if not account_id:
            raise IncomeSyncBaseException(
                "AccountId не найден. Активируйте приложение через Vendor API"
            )
        return account_id

    async def initialize(self) -> IncomeSyncSetupResult:
        """Создать/доинициализировать инфраструктуру для текущего аккаунта."""
        account_id = self._require_account_id()
        result = IncomeSyncSetupResult(account_id=account_id)
        config = await self._uow.configs.get_by_account_id(account_id)

        # 1. Справочник «Статьи доходов»
        dictionary_id = config.dictionary_id if config else None
        if not dictionary_id:
            dictionary = await self._customentity_service.create_dictionary(
                DICTIONARY_NAME
            )
            dictionary_id = dictionary.id
            await self._uow.configs.upsert(account_id, dictionary_id=dictionary_id)
            await self._uow.commit()
            logger.info(
                "Создан справочник статей доходов: account_id=%s, id=%s",
                account_id,
                dictionary_id,
            )
        result.dictionary_id = dictionary_id

        # 2. Доп. поля (adopt-or-create + защита от коллизии имени)
        result.counterparty_attribute_id = await self._ensure_attribute(
            account_id=account_id,
            field_name="counterparty_attribute_id",
            current_id=config.counterparty_attribute_id if config else None,
            label="контрагента",
            attribute_name=COUNTERPARTY_ATTRIBUTE_NAME,
            dictionary_id=dictionary_id,
            find=self._counterparty_service.find_customentity_attribute_by_name,
            create=self._counterparty_service.create_customentity_attribute,
            result=result,
        )
        for entity_type, label in (
            ("paymentin", "входящего платежа"),
            ("cashin", "приходного ордера"),
        ):
            service = self._payment_services[entity_type]
            field_name = f"{entity_type}_attribute_id"
            attribute_id = await self._ensure_attribute(
                account_id=account_id,
                field_name=field_name,
                current_id=getattr(config, field_name) if config else None,
                label=label,
                attribute_name=PAYMENT_ATTRIBUTE_NAME,
                dictionary_id=dictionary_id,
                find=service.find_customentity_attribute_by_name,
                create=service.create_customentity_attribute,
                result=result,
            )
            setattr(result, field_name, attribute_id)

        # 3. Вебхуки на создание входящих платежей/ордеров
        await self._register_webhooks(result)

        # 4. Автопроставление включаем после успешной инициализации.
        config = await self._uow.configs.get_by_account_id(account_id)
        if config and config.is_initialized:
            await self._uow.configs.upsert(account_id, enabled=True)
            await self._uow.commit()

        logger.info(
            "Инициализация статьи доходов: account_id=%s, success=%s, errors=%s",
            account_id,
            result.success,
            result.errors,
        )
        return result

    async def _ensure_attribute(
        self,
        *,
        account_id: str,
        field_name: str,
        current_id: Optional[str],
        label: str,
        attribute_name: str,
        dictionary_id: str,
        find: Callable[[str], Awaitable[Optional[dict]]],
        create: Callable[[str, str], Awaitable[dict]],
        result: IncomeSyncSetupResult,
    ) -> Optional[str]:
        """Вернуть id доп. поля, при необходимости найдя или создав его."""
        if current_id:
            return current_id

        try:
            existing = await find(attribute_name)
            if existing is None:
                created = await create(attribute_name, dictionary_id)
                attribute_id = created.get("id")
                logger.info(
                    "Создано доп. поле %s: account_id=%s, attribute_id=%s",
                    label,
                    account_id,
                    attribute_id,
                )
            elif existing.get("customentity_id") == dictionary_id:
                # Наше же поле — идемпотентный повторный запуск, переиспользуем.
                attribute_id = existing.get("id")
                logger.info(
                    "Доп. поле %s уже существует, переиспользуем: %s", label, attribute_id
                )
            else:
                msg = (
                    f"Доп. поле {label} «{attribute_name}» уже существует "
                    f"(id={existing.get('id')}) и ссылается на другой справочник "
                    f"({existing.get('customentity_id')}), а не на «{DICTIONARY_NAME}» "
                    f"({dictionary_id}). Удалите или переименуйте это поле в МойСклад "
                    "и повторите инициализацию."
                )
                result.errors.append(msg)
                logger.warning(msg)
                return None
        except (CounterpartyAPIError, PaymentAPIError) as exc:
            msg = f"Не удалось создать доп. поле {label}: {exc.message} {exc.details}"
            result.errors.append(msg)
            logger.warning(msg)
            return None

        if attribute_id:
            await self._uow.configs.upsert(account_id, **{field_name: attribute_id})
            await self._uow.commit()
        return attribute_id

    async def _register_webhooks(self, result: IncomeSyncSetupResult) -> None:
        """Зарегистрировать (или включить) вебхуки paymentin/cashin CREATE."""
        webhook_url = settings.ms_webhook_url
        if not webhook_url:
            result.errors.append(
                "MS_WEBHOOK_URL не задан — вебхуки статьи доходов не зарегистрированы"
            )
            logger.warning("MS_WEBHOOK_URL не задан, пропускаем регистрацию вебхуков")
            return

        # Локальный импорт во избежание циклической зависимости hooks <-> income_sync.
        from ...hooks.services.moysklad_client import MoySkladClient
        from ...hooks.services.shared_webhooks import ensure_webhooks_enabled

        ensured = await ensure_webhooks_enabled(
            MoySkladClient(self._auth_service),
            webhook_url,
            [
                (entity_type, INCOME_PAYMENT_WEBHOOK_ACTION)
                for entity_type in INCOME_PAYMENT_ENTITY_TYPES
            ],
        )
        result.webhooks_created += ensured.created
        result.webhooks_existing += ensured.existing + ensured.enabled
        result.errors.extend(ensured.errors)
