"""Сервис для работы со статьями расходов."""

import logging
from typing import List, Optional

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import ExpenseItemEntity
from .expenseitem_client import ExpenseItemClient

logger = logging.getLogger(__name__)


class ExpenseItemService:
    """Сервис для работы со статьями расходов (expenseitem)."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._client = ExpenseItemClient(auth_service)

    @property
    def entity_type(self) -> str:
        return "expenseitem"

    async def list_all(self) -> List[ExpenseItemEntity]:
        """Получить все статьи расходов."""
        rows = await self._client.list_all()
        return [self._to_entity(row) for row in rows]

    async def get_by_id(self, item_id: str) -> ExpenseItemEntity:
        """Получить статью расходов по ID."""
        data = await self._client.get_by_id(item_id)
        return self._to_entity(data)

    async def create(
        self,
        name: str,
        description: Optional[str] = None,
        code: Optional[str] = None,
        external_code: Optional[str] = None,
    ) -> ExpenseItemEntity:
        """Создать статью расходов."""
        payload: dict = {"name": name}
        if description is not None:
            payload["description"] = description
        if code is not None:
            payload["code"] = code
        if external_code is not None:
            payload["externalCode"] = external_code

        data = await self._client.create(payload)
        return self._to_entity(data)

    async def update(
        self,
        item_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        code: Optional[str] = None,
        external_code: Optional[str] = None,
    ) -> ExpenseItemEntity:
        """Обновить статью расходов (только переданные поля)."""
        payload: dict = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if code is not None:
            payload["code"] = code
        if external_code is not None:
            payload["externalCode"] = external_code

        data = await self._client.update(item_id, payload)
        return self._to_entity(data)

    async def delete(self, item_id: str) -> bool:
        """Удалить статью расходов."""
        return await self._client.delete(item_id)

    @staticmethod
    def _to_entity(data: dict) -> ExpenseItemEntity:
        return ExpenseItemEntity(
            id=data["id"],
            name=data["name"],
            meta_href=data.get("meta", {}).get("href", ""),
            description=data.get("description"),
            code=data.get("code"),
            external_code=data.get("externalCode"),
            account_id=data.get("accountId"),
            updated=data.get("updated"),
        )
