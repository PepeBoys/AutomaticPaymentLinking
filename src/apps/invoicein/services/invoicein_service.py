"""Сервис для работы со счетами покупателю."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import InvoiceInEntity
from ..exceptions import InvoiceInNotFoundError
from .invoicein_client import InvoiceInClient

logger = logging.getLogger(__name__)


class InvoiceInService:
    """Сервис для работы со счетами покупателю."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._client = InvoiceInClient(auth_service)

    async def get_states(self) -> list[dict]:
        """Получить статусы счетов покупателю."""

        return await self._client.get_states()

    async def find_for_payment(
        self,
        agent_id: str,
        payment_sum: float,
        search_by_sum: bool = True,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ) -> List[InvoiceInEntity]:
        """Найти счета для привязки платежа."""
        if search_by_sum:
            invoices_data = await self._client.search_by_agent_and_sum(
                agent_id=agent_id,
                sum_value=payment_sum,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )
        else:
            invoices_data = await self._client.search_by_agent(
                agent_id=agent_id,
                organization_id=organization_id,
                date_from=datetime.now(timezone.utc) - timedelta(days=60),
                limit=10,
                order="moment,asc" if prioritize_oldest else "moment,desc",
            )

        entities = [self._to_entity(data) for data in invoices_data]
        entities = [entity for entity in entities if not entity.is_fully_paid()]

        logger.info(
            "Найдено счетов для привязки: %d (agent=%s, sum=%s, by_sum=%s)",
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
    ) -> InvoiceInEntity:
        """Найти счет покупателю по номеру и контрагенту."""

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

        invoices_data = await self._client.search(
            filter_str=";".join(filter_parts),
            limit=10 if moment else 100,
            order="moment,asc" if prioritize_oldest else "moment,desc",
        )

        if not invoices_data:
            raise InvoiceInNotFoundError(
                f"Счет с номером '{name}' для контрагента {agent_id} не найден"
            )

        return self._to_entity(invoices_data[0])

    @staticmethod
    def _to_entity(data: dict) -> InvoiceInEntity:
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
            raise InvoiceInNotFoundError("Некорректные данные счета покупателю")

        return InvoiceInEntity(
            id=data["id"],
            account_id=data["accountId"],
            name=data["name"],
            moment=data["moment"],
            applicable=data.get("applicable", False),
            sum=data["sum"],
            payed_sum=data.get("payedSum", 0),
            agent_id=agent_id,
            organization_id=org_id,
            meta_href=data["meta"]["href"],
            project_meta_href=project_href,
        )

    async def update_state(self, invoice_id: str, state_id: str) -> InvoiceInEntity:
        """Обновить статус счета покупателю."""

        data = await self._client.update_state(invoice_id, state_id)
        return self._to_entity(data)
