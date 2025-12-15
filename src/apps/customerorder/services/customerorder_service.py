"""Сервис для работы с заказами покупателя."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import CustomerOrderEntity
from ..domain.value_objects import CustomerOrderFilter
from ..exceptions import CustomerOrderNotFoundError
from .customerorder_client import CustomerOrderClient

logger = logging.getLogger(__name__)


class CustomerOrderService:
    """
    Сервис для работы с заказами покупателя.
    
    Реализует бизнес-логику поиска и работы с заказами.
    """
    
    def __init__(self, auth_service: MySkladAuthService) -> None:
        """
        Инициализировать сервис.
        
        Args:
            auth_service: Сервис аутентификации
        """
        self._auth_service = auth_service
        self._client = CustomerOrderClient(auth_service)

    async def get_states(self) -> list[dict]:
        """Получить статусы заказов покупателя."""

        return await self._client.get_states()

    async def get_by_id(self, order_id: str) -> CustomerOrderEntity:
        """
        Получить заказ по ID.
        
        Args:
            order_id: ID заказа
            
        Returns:
            Доменная сущность заказа
        """
        data = await self._client.get_by_id(order_id)
        return self._to_entity(data)
    
    async def find_for_payment(
        self,
        agent_id: str,
        payment_sum: float,
        search_by_sum: bool = True,
        prioritize_oldest: bool = True,
    ) -> List[CustomerOrderEntity]:
        """
        Найти заказы для привязки платежа.
        
        Args:
            agent_id: ID контрагента
            payment_sum: Сумма платежа
            search_by_sum: Искать по точной сумме
            
        Returns:
            Список подходящих заказов
        """
        if search_by_sum:
            orders_data = await self._client.search_by_agent_and_sum(
                agent_id=agent_id,
                sum_value=payment_sum,
                prioritize_oldest=prioritize_oldest,
            )
        else:
            orders_data = await self._client.search_by_agent(
                agent_id=agent_id,
                only_unpaid=True,
                date_from=datetime.now(timezone.utc) - timedelta(days=60),
                limit=10,
                order="moment,asc" if prioritize_oldest else "moment,desc",
            )
        
        entities = [self._to_entity(data) for data in orders_data]
        
        entities = [e for e in entities if not e.is_fully_paid()]
        
        logger.info(
            "Найдено заказов для привязки: %d (agent=%s, sum=%s, by_sum=%s)",
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
        moment: Optional[datetime] = None,
        prioritize_oldest: bool = True,
    ) -> CustomerOrderEntity:
        """Найти заказ по номеру и контрагенту."""
        filter_parts = [
            f"agent=https://api.moysklad.ru/api/remap/1.2/entity/counterparty/{agent_id}",
            f"name={name}",
        ]

        if moment:
            start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
            end = moment.replace(hour=23, minute=59, second=59, microsecond=999999)
            filter_parts.append(f"moment>={start.strftime('%Y-%m-%d %H:%M:%S')}")
            filter_parts.append(f"moment<={end.strftime('%Y-%m-%d %H:%M:%S')}")

        filter_str = ";".join(filter_parts)
        orders_data = await self._client.search(
            filter_str=filter_str,
            limit=10 if moment else 100,
            order="moment,asc" if prioritize_oldest else "moment,desc",
        )

        if not orders_data:
            raise CustomerOrderNotFoundError(
                f"Заказ с номером '{name}' для контрагента {agent_id} не найден"
            )
        
        return self._to_entity(orders_data[0])
    
    @staticmethod
    def _to_entity(data: dict) -> CustomerOrderEntity:
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
        
        return CustomerOrderEntity(
            id=data["id"],
            account_id=data["accountId"],
            name=data["name"],
            moment=data["moment"],
            applicable=data["applicable"],
            sum=data["sum"],
            payed_sum=data.get("payedSum", 0),
            shipped_sum=data.get("shippedSum", 0),
            invoiced_sum=data.get("invoicedSum", 0),
            agent_id=agent_id,
            organization_id=org_id,
            meta_href=data["meta"]["href"],
            project_meta_href=project_href,
        )

    async def update_state(self, order_id: str, state_id: str) -> CustomerOrderEntity:
        """Обновить статус заказа покупателя."""

        data = await self._client.update_state(order_id, state_id)
        return self._to_entity(data)
