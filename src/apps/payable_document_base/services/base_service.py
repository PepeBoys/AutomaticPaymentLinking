"""Базовый сервис для оплачиваемых документов."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Generic, List, Optional, TypeVar

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import BasePayableDocumentEntity
from ..exceptions import DocumentNotFoundError
from .base_client import BaseDocumentClient

TEntity = TypeVar("TEntity", bound=BasePayableDocumentEntity)
TClient = TypeVar("TClient", bound=BaseDocumentClient)

logger = logging.getLogger(__name__)


class BaseDocumentService(Generic[TEntity, TClient], ABC):
    """Общая бизнес-логика для документов."""

    def __init__(self, auth_service: MySkladAuthService, client: TClient) -> None:
        self._auth_service = auth_service
        self._client = client

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """Тип сущности (invoicein/invoiceout/...))."""

    @abstractmethod
    def _to_entity(self, data: dict) -> TEntity:
        """Преобразовать данные API в доменную сущность."""

    async def get_states(self) -> list[dict]:
        """Получить статусы документов."""
        return await self._client.get_states()

    async def find_for_payment(
        self,
        agent_id: str,
        payment_sum: float,
        search_by_sum: bool = True,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ) -> List[TEntity]:
        """Найти документы для привязки платежа."""
        if search_by_sum:
            documents_data = await self._client.search_by_agent_and_sum(
                agent_id=agent_id,
                sum_value=payment_sum,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )
        else:
            documents_data = await self._client.search_by_agent(
                agent_id=agent_id,
                organization_id=organization_id,
                date_from=datetime.now(timezone.utc) - timedelta(days=60),
                limit=10,
                order="moment,asc" if prioritize_oldest else "moment,desc",
            )

        entities = [self._to_entity(data) for data in documents_data]

        if search_by_sum:
            entities = [entity for entity in entities if entity.payed_sum == 0]
        else:
            entities = [entity for entity in entities if not entity.is_fully_paid()]

        logger.info(
            "Найдено документов для привязки: %d (agent=%s, sum=%s, by_sum=%s)",
            len(entities),
            agent_id,
            payment_sum,
            search_by_sum,
        )

        return entities

    async def find_by_name_and_agent(
        self,
        name: str,
        agent_id: str,
        organization_id: str | None = None,
        moment: Optional[datetime] = None,
        prioritize_oldest: bool = True,
    ) -> TEntity:
        """Найти документ по номеру и контрагенту."""

        filter_parts = [
            f"agent=https://api.moysklad.ru/api/remap/1.2/entity/counterparty/{agent_id}",
            f"name={name}",
        ]

        if organization_id:
            filter_parts.append(
                "organization=https://api.moysklad.ru/api/remap/1.2/entity/organization/"
                f"{organization_id}"
            )

        if moment:
            msk_tz = timezone(timedelta(hours=3))

            start = moment.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(
                msk_tz
            )
            end = moment.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(
                msk_tz
            )

            filter_parts.append(f"moment>={start.strftime('%Y-%m-%d %H:%M:%S')}")
            filter_parts.append(f"moment<={end.strftime('%Y-%m-%d %H:%M:%S')}")

        documents_data = await self._client.search(
            filter_str=";".join(filter_parts),
            limit=10 if moment else 100,
            order="moment,asc" if prioritize_oldest else "moment,desc",
        )

        if not documents_data:
            raise DocumentNotFoundError(
                f"Документ с номером '{name}' для контрагента {agent_id} не найден"
            )

        return self._to_entity(documents_data[0])

    async def update_state(self, document_id: str, state_id: str) -> TEntity:
        """Обновить статус документа."""

        data = await self._client.update_state(document_id, state_id)
        return self._to_entity(data)

    async def get_by_id(self, document_id: str) -> TEntity:
        """Получить документ по идентификатору."""
        data = await self._client.get_by_id(document_id)
        return self._to_entity(data)
