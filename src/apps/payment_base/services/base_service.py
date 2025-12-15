"""Базовый сервис для работы с платежами."""

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import BasePaymentEntity
from .base_client import BasePaymentClient

TEntity = TypeVar("TEntity", bound=BasePaymentEntity)
TClient = TypeVar("TClient", bound=BasePaymentClient)

logger = logging.getLogger(__name__)


class BasePaymentService(Generic[TEntity, TClient], ABC):
    """Базовая логика работы с платежами."""

    def __init__(self, auth_service: MySkladAuthService, client: TClient) -> None:
        self._auth_service = auth_service
        self._client = client

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """Тип сущности (paymentin/paymentout/cashin/cashout)."""

    @abstractmethod
    def _to_entity(self, data: dict) -> TEntity:
        """Преобразовать данные API в доменную сущность."""

    async def get_by_id(self, payment_id: str) -> TEntity:
        """Получить платеж по ID."""
        base_url = self._client._get_base_url()
        href = f"{base_url}/entity/{self.entity_type}/{payment_id}"
        data = await self._client.get_by_href(href)
        return self._to_entity(data)

    async def get_by_href(self, href: str) -> TEntity:
        """Получить платеж по href."""
        data = await self._client.get_by_href(href)
        return self._to_entity(data)

    async def get_states(self) -> list[dict]:
        """Получить список статусов платежей из МойСклад."""
        return await self._client.get_states()

    async def update_state(self, payment_id: str, state_id: str) -> TEntity:
        """Установить статус платежа."""
        data = await self._client.update_state(payment_id, state_id)
        return self._to_entity(data)

    async def link_to_document(
        self, payment_id: str, document_meta_href: str, linked_sum: float
    ) -> TEntity:
        """Привязать платеж к документу."""
        payment_data = await self._client.get_by_href(
            f"{self._client._get_base_url()}/entity/{self.entity_type}/{payment_id}"
        )
        payment = self._to_entity(payment_data)

        operations = [
            {"meta": op["meta"], "linkedSum": op.get("linkedSum", 0)}
            for op in payment.linked_operations
        ]

        operations.append(
            {
                "meta": {
                    "href": document_meta_href,
                    "type": self._extract_type_from_href(document_meta_href),
                    "mediaType": "application/json",
                },
                "linkedSum": linked_sum,
            }
        )

        updated_data = await self._client.update_operations(payment_id, operations)
        return self._to_entity(updated_data)

    async def update_project(self, payment_id: str, project_href: str) -> TEntity:
        """Обновить проект платежа."""
        updated_data = await self._client.update_project(payment_id, project_href)
        return self._to_entity(updated_data)

    @staticmethod
    def _extract_type_from_href(href: str) -> str:
        """Извлечь тип документа из href."""
        parts = href.split("/")
        return parts[-2] if len(parts) >= 2 else "unknown"
