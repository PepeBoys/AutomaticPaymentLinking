"""Сервис для работы с приходными ордерами."""

import logging

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import CashInEntity
from .cashin_client import CashInClient

logger = logging.getLogger(__name__)


class CashInService:
    """Сервис для работы с приходными ордерами."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._client = CashInClient(auth_service)

    async def get_by_id(self, payment_id: str) -> CashInEntity:
        """
        Получить приходный ордер по ID.
        
        Args:
            payment_id: ID приходного ордера
            
        Returns:
            Доменная сущность платежа
        """
        base_url = self._client._get_base_url()
        href = f"{base_url}/entity/cashin/{payment_id}"
        data = await self._client.get_by_href(href)
        return self._to_entity(data)

    async def get_by_href(self, href: str) -> CashInEntity:
        """
        Получить приходный ордер по href.

        Args:
            href: Полный href приходного ордера

        Returns:
            Доменная сущность платежа
        """
        data = await self._client.get_by_href(href)
        return self._to_entity(data)

    async def get_states(self) -> list[dict]:
        """Получить список статусов приходных ордеров из МойСклад."""
        return await self._client.get_states()

    async def update_state(self, payment_id: str, state_id: str) -> CashInEntity:
        """Установить статус приходного ордера."""

        data = await self._client.update_state(payment_id, state_id)
        return self._to_entity(data)

    async def link_to_document(
        self, payment_id: str, document_meta_href: str, linked_sum: float
    ) -> CashInEntity:
        """
        Привязать приходный ордер к документу.
        
        Args:
            payment_id: ID приходного ордера
            document_meta_href: href документа для привязки
            linked_sum: Сумма привязки
            
        Returns:
            Обновленная сущность приходного ордера
        """
        payment_data = await self._client.get_by_href(
            f"{self._client._get_base_url()}/entity/cashin/{payment_id}"
        )
        payment = self._to_entity(payment_data)
        
        operations = [
            {"meta": op["meta"], "linkedSum": op.get("linkedSum", 0)}
            for op in payment.linked_operations
        ]
        
        operations.append({
            "meta": {
                "href": document_meta_href,
                "type": self._extract_type_from_href(document_meta_href),
                "mediaType": "application/json",
            },
            "linkedSum": linked_sum,
        })
        
        updated_data = await self._client.update_operations(payment_id, operations)
        return self._to_entity(updated_data)

    async def update_project(self, payment_id: str, project_href: str) -> CashInEntity:
        """Обновить проект приходного ордера."""

        updated_data = await self._client.update_project(payment_id, project_href)
        return self._to_entity(updated_data)
    
    @staticmethod
    def _to_entity(data: dict) -> CashInEntity:
        """
        Преобразовать данные API в доменную сущность.
        
        Args:
            data: Данные от API
            
        Returns:
            Доменная сущность
        """
        agent_meta = data.get("agent", {}).get("meta", {})
        agent_href = agent_meta.get("href", "")
        agent_id = agent_href.split("/")[-1] if agent_href else ""
        
        org_meta = data.get("organization", {}).get("meta", {})
        org_href = org_meta.get("href", "")
        org_id = org_href.split("/")[-1] if org_href else ""

        project_meta = data.get("project", {}).get("meta", {})
        project_href = project_meta.get("href") if project_meta else None
        
        linked_ops = [
            {
                "meta": {
                    "href": op.get("meta", {}).get("href", ""),
                    "type": op.get("meta", {}).get("type", ""),
                },
                "linkedSum": op.get("linkedSum", 0),
            }
            for op in data.get("operations", [])
        ]
        
        return CashInEntity(
            id=data["id"],
            account_id=data["accountId"],
            name=data["name"],
            moment=data["moment"],
            applicable=data["applicable"],
            sum=data["sum"],
            agent_id=agent_id,
            organization_id=org_id,
            payment_purpose=data.get("paymentPurpose"),
            linked_operations=linked_ops,
            meta_href=data["meta"]["href"],
            project_meta_href=project_href,
        )
    
    @staticmethod
    def _extract_type_from_href(href: str) -> str:
        """
        Извлечь тип документа из href.
        
        Args:
            href: href документа
            
        Returns:
            Тип документа
        """
        parts = href.split("/")
        return parts[-2] if len(parts) >= 2 else "unknown"