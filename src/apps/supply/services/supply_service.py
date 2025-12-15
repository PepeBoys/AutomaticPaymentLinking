"""Сервис для работы с отгрузками (supply)."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import SupplyEntity
from ..exceptions import SupplyNotFoundError
from .supply_client import SupplyClient

logger = logging.getLogger(__name__)


class SupplyService:
    """Сервис для работы с отгрузками."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._client = SupplyClient(auth_service)

    async def get_states(self) -> list[dict]:
        """Получить статусы отгрузок."""

        return await self._client.get_states()

    async def find_for_payment(
        self,
        agent_id: str,
        payment_sum: float,
        search_by_sum: bool = True,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ) -> List[SupplyEntity]:
        """Найти отгрузки для привязки платежа."""

        if search_by_sum:
            supplys_data = await self._client.search_by_agent_and_sum(
                agent_id=agent_id,
                sum_value=payment_sum,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )
        else:
            supplys_data = await self._client.search_by_agent(
                agent_id=agent_id,
                organization_id=organization_id,
                date_from=datetime.now(timezone.utc) - timedelta(days=60),
                limit=10,
                order="moment,asc" if prioritize_oldest else "moment,desc"
            )

        entities = [self._to_entity(data) for data in supplys_data]
        entities = [entity for entity in entities if not entity.is_fully_paid()]

        logger.info(
            "Найдено отгрузок для привязки: %d (agent=%s, sum=%s, by_sum=%s)",
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
    ) -> SupplyEntity:
        """Найти отгрузку по номеру и контрагенту."""

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

            start = moment.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(msk_tz)
            end = moment.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(msk_tz)

            filter_parts.append(f"moment>={start.strftime('%Y-%m-%d %H:%M:%S')}")
            filter_parts.append(f"moment<={end.strftime('%Y-%m-%d %H:%M:%S')}")

        supplys_data = await self._client.search(
            filter_str=";".join(filter_parts),
            limit=10 if moment else 100,
            order="moment,asc" if prioritize_oldest else "moment,desc",
        )

        if not supplys_data:
            raise SupplyNotFoundError(
                f"Отгрузка с номером '{name}' для контрагента {agent_id} не найдена"
            )

        return self._to_entity(supplys_data[0])

    @staticmethod
    def _to_entity(data: dict) -> SupplyEntity:
        """Преобразовать данные API в доменную сущность."""

        agent_meta = data.get("agent", {}).get("meta", {})
        agent_href = agent_meta.get("href", "")
        agent_id = agent_href.split("/")[-1] if agent_href else ""

        org_meta = data.get("organization", {}).get("meta", {})
        org_href = org_meta.get("href", "")
        org_id = org_href.split("/")[-1] if org_href else ""

        project_meta = data.get("project", {}).get("meta", {})
        project_href = project_meta.get("href") if project_meta else None

        if not data.get("meta", {}).get("href"):
            raise SupplyNotFoundError("Некорректные данные отгрузки")

        return SupplyEntity(
            id=data["id"],
            account_id=data["accountId"],
            name=data.get("name", ""),
            moment=data["moment"],
            applicable=data.get("applicable", False),
            sum=data.get("sum", 0),
            payed_sum=data.get("payedSum", 0),
            agent_id=agent_id,
            organization_id=org_id,
            meta_href=data["meta"]["href"],
            project_meta_href=project_href,
        )
    
    async def update_state(self, supply_id: str, state_id: str) -> SupplyEntity:
        """Обновить статус отгрузки."""

        data = await self._client.update_state(supply_id, state_id)
        return self._to_entity(data)