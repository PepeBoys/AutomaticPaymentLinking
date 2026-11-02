"""Проставление статьи доходов во входящие платежи и приходные ордера."""

import logging
from typing import Optional

from ...counterparty.exceptions import CounterpartyNotFoundError
from ...counterparty.services.counterparty_service import CounterpartyService
from ...ms_auth.services.auth_service import MySkladAuthService
from ..uow.unit_of_work import IncomeSyncUnitOfWork

logger = logging.getLogger(__name__)


class IncomeSyncHandler:
    """Обработчик вебхуков paymentin/cashin CREATE для статьи доходов."""

    def __init__(
        self,
        auth_service: MySkladAuthService,
        uow: IncomeSyncUnitOfWork,
        counterparty_service: CounterpartyService,
    ) -> None:
        self._auth_service = auth_service
        self._uow = uow
        self._counterparty_service = counterparty_service

    async def apply_income_item_to_payment(
        self, account_id: str, href: str, payment_service
    ) -> None:
        """Проставить статью доходов в paymentin/cashin по контрагенту.

        Цепочка: платёж → контрагент → доп. поле (ссылка на элемент
        справочника «Статьи доходов») → доп. поле платежа.

        Заполненную вручную статью не перезаписываем. Не бросает исключений:
        сбои логируются и не прерывают остальную обработку вебхука.
        """
        config = await self._uow.configs.get_by_account_id(account_id)
        if not config or not config.enabled or not config.is_initialized:
            return

        payment_attribute_id = config.payment_attribute_id(payment_service.entity_type)

        try:
            payment = await payment_service.get_by_href(href)
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            logger.warning("Не удалось получить платёж для статьи доходов: %s", exc)
            return

        if payment.get_attribute_value(payment_attribute_id):
            logger.info(
                "Статья доходов в платеже %s уже заполнена, не перезаписываем", payment.id
            )
            return

        if not payment.agent_id:
            logger.info("У платежа %s нет контрагента, пропуск статьи доходов", payment.id)
            return

        try:
            counterparty = await self._counterparty_service.get_by_id(payment.agent_id)
        except CounterpartyNotFoundError:
            logger.warning("Контрагент %s не найден для статьи доходов", payment.agent_id)
            return
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            logger.warning("Не удалось получить контрагента %s: %s", payment.agent_id, exc)
            return

        value = counterparty.get_attribute_value(config.counterparty_attribute_id)
        element_href = self._extract_element_href(value)
        if not element_href:
            logger.info(
                "У контрагента %s не заполнено доп. поле статьи доходов, пропуск",
                payment.agent_id,
            )
            return

        try:
            await payment_service.update_customentity_attribute(
                payment.id, payment_attribute_id, element_href
            )
            logger.info(
                "✓ Статья доходов '%s' проставлена в %s %s (контрагент %s)",
                value.get("name"),
                payment_service.entity_type,
                payment.id,
                payment.agent_id,
            )
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            logger.warning(
                "Не удалось проставить статью доходов в платёж %s: %s", payment.id, exc
            )

    @staticmethod
    def _extract_element_href(value) -> Optional[str]:
        """href элемента справочника из значения доп. поля {meta: {href}, name}."""
        if isinstance(value, dict):
            meta = value.get("meta")
            if isinstance(meta, dict):
                return meta.get("href")
        return None
