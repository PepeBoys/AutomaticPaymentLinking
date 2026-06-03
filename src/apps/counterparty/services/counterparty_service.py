"""Сервис для работы с контрагентами."""

import logging
from typing import Optional

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import CounterpartyEntity
from .counterparty_client import CounterpartyClient

logger = logging.getLogger(__name__)


class CounterpartyService:
    """Сервис для работы с контрагентами (counterparty)."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._client = CounterpartyClient(auth_service)

    @property
    def entity_type(self) -> str:
        return "counterparty"

    async def get_by_id(self, agent_id: str) -> CounterpartyEntity:
        """Получить контрагента (с доп. полями) по ID."""
        data = await self._client.get_by_id(agent_id)
        return self._to_entity(data)

    async def get_metadata(self) -> dict:
        """Получить сырые метаданные контрагента."""
        return await self._client.get_metadata()

    async def create_customentity_attribute(
        self,
        name: str,
        customentity_metadata_id: str,
        *,
        required: bool = False,
        show: bool = True,
        description: Optional[str] = None,
    ) -> dict:
        """Создать доп. поле контрагента типа «справочник» (customentity).

        Args:
            name: Наименование доп. поля.
            customentity_metadata_id: ID пользовательского справочника, на
                который ссылается доп. поле.
            required: Является ли поле обязательным.
            show: Показывать ли поле на UI.
            description: Описание доп. поля.

        Returns:
            Сырой ответ МС с описанием созданного доп. поля (содержит id).
        """
        base_url = self._client._get_base_url()
        custom_entity_meta_href = (
            f"{base_url}/entity/customentity/{customentity_metadata_id}/metadata"
        )

        payload: dict = {
            "name": name,
            "type": "customentity",
            "required": required,
            "show": show,
            "customEntityMeta": {
                "href": custom_entity_meta_href,
                "type": "customentitymetadata",
                "mediaType": "application/json",
            },
        }
        if description is not None:
            payload["description"] = description

        return await self._client.create_attribute(payload)

    @staticmethod
    def _to_entity(data: dict) -> CounterpartyEntity:
        return CounterpartyEntity(
            id=data["id"],
            name=data.get("name", ""),
            meta_href=data.get("meta", {}).get("href", ""),
            attributes=data.get("attributes", []) or [],
            account_id=data.get("accountId"),
        )
