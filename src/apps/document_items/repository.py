"""Репозиторий настроек статей в первичных документах."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .constants import DOCUMENT_TYPES
from .models import DocumentItemsConfig


def attribute_field(document_type: str) -> str:
    return f"{document_type}_attribute_id"


class DocumentItemsConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, account_id: str) -> Optional[DocumentItemsConfig]:
        stmt = select(DocumentItemsConfig).where(
            DocumentItemsConfig.ms_account_id == account_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, account_id: str) -> DocumentItemsConfig:
        config = await self.get(account_id)
        if config is None:
            config = DocumentItemsConfig(
                ms_account_id=account_id, income_mode="off", expense_mode="off"
            )
            self._session.add(config)
            await self._session.flush()
        return config

    async def set_attribute(
        self, account_id: str, document_type: str, attribute_id: Optional[str]
    ) -> None:
        if document_type not in DOCUMENT_TYPES:
            raise ValueError(f"Неизвестный тип документа: {document_type}")
        config = await self.get_or_create(account_id)
        setattr(config, attribute_field(document_type), attribute_id)
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
