"""Сервис для работы с пользовательскими справочниками."""

import logging
from typing import List, Optional

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import CustomEntityDictionary, CustomEntityElementEntity
from .customentity_client import CustomEntityClient

logger = logging.getLogger(__name__)


class CustomEntityService:
    """Сервис для работы с пользовательскими справочниками (customentity)."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._client = CustomEntityClient(auth_service)

    @property
    def entity_type(self) -> str:
        return "customentity"

    # ----- Справочник -----

    async def create_dictionary(self, name: str) -> CustomEntityDictionary:
        """Создать новый справочник."""
        data = await self._client.create_dictionary(name)
        return CustomEntityDictionary(
            id=data["id"],
            name=data["name"],
            meta_href=data.get("meta", {}).get("href", ""),
        )

    async def get_metadata(self, metadata_id: str) -> dict:
        """Получить сырые метаданные справочника."""
        return await self._client.get_metadata(metadata_id)

    # ----- Элементы -----

    async def list_elements(self, metadata_id: str) -> List[CustomEntityElementEntity]:
        """Получить все элементы справочника."""
        rows = await self._client.list_elements(metadata_id)
        return [self._to_entity(row) for row in rows]

    async def get_element(
        self, metadata_id: str, element_id: str
    ) -> CustomEntityElementEntity:
        """Получить элемент справочника по ID."""
        data = await self._client.get_element(metadata_id, element_id)
        return self._to_entity(data)

    async def create_element(
        self,
        metadata_id: str,
        name: str,
        description: Optional[str] = None,
        code: Optional[str] = None,
        external_code: Optional[str] = None,
    ) -> CustomEntityElementEntity:
        """Создать элемент справочника."""
        payload: dict = {"name": name}
        if description is not None:
            payload["description"] = description
        if code is not None:
            payload["code"] = code
        if external_code is not None:
            payload["externalCode"] = external_code

        data = await self._client.create_element(metadata_id, payload)
        return self._to_entity(data)

    async def update_element(
        self,
        metadata_id: str,
        element_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        code: Optional[str] = None,
        external_code: Optional[str] = None,
    ) -> CustomEntityElementEntity:
        """Обновить элемент справочника (только переданные поля)."""
        payload: dict = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if code is not None:
            payload["code"] = code
        if external_code is not None:
            payload["externalCode"] = external_code

        data = await self._client.update_element(metadata_id, element_id, payload)
        return self._to_entity(data)

    async def delete_element(self, metadata_id: str, element_id: str) -> bool:
        """Удалить элемент справочника."""
        return await self._client.delete_element(metadata_id, element_id)

    @staticmethod
    def _to_entity(data: dict) -> CustomEntityElementEntity:
        return CustomEntityElementEntity(
            id=data["id"],
            name=data["name"],
            meta_href=data.get("meta", {}).get("href", ""),
            code=data.get("code"),
            description=data.get("description"),
            external_code=data.get("externalCode"),
            account_id=data.get("accountId"),
            updated=data.get("updated"),
        )
