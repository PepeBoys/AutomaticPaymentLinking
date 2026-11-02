"""Репозиторий настроек фичи автопроставления статьи доходов."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.entities import ATTRIBUTE_FIELDS, IncomeSyncConfig
from ..exceptions import IncomeSyncRepositoryError
from ..models import IncomeItemSyncConfig

logger = logging.getLogger(__name__)

_ID_FIELDS = ("dictionary_id", *ATTRIBUTE_FIELDS)


class IncomeSyncConfigRepository:
    """Доступ к настройкам фичи (одна запись на аккаунт)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_model(self, account_id: str) -> Optional[IncomeItemSyncConfig]:
        stmt = select(IncomeItemSyncConfig).where(
            IncomeItemSyncConfig.ms_account_id == account_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_account_id(self, account_id: str) -> Optional[IncomeSyncConfig]:
        model = await self._get_model(account_id)
        return self._to_entity(model) if model else None

    async def upsert(
        self,
        account_id: str,
        *,
        enabled: Optional[bool] = None,
        **ids: Optional[str],
    ) -> IncomeSyncConfig:
        """Создать или частично обновить настройки аккаунта.

        ``ids`` — поля с id инфраструктуры (dictionary_id, *_attribute_id).
        None означает «не трогать».
        """
        if not account_id or not account_id.strip():
            raise IncomeSyncRepositoryError("ms_account_id is required")

        unknown = set(ids) - set(_ID_FIELDS)
        if unknown:
            raise IncomeSyncRepositoryError(f"Неизвестные поля конфига: {unknown}")

        model = await self._get_model(account_id)
        if model is None:
            model = IncomeItemSyncConfig(ms_account_id=account_id, enabled=bool(enabled))
            self._session.add(model)
        elif enabled is not None:
            model.enabled = enabled

        for name, value in ids.items():
            if value is not None:
                setattr(model, name, value)

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def clear_attribute(self, account_id: str, field_name: str) -> bool:
        """Сбросить ссылку на удалённое в МС доп. поле и выключить фичу."""
        if field_name not in ATTRIBUTE_FIELDS:
            raise IncomeSyncRepositoryError(f"Неизвестное доп. поле: {field_name}")

        model = await self._get_model(account_id)
        if not model:
            return False
        setattr(model, field_name, None)
        model.enabled = False
        await self._session.flush()
        return True

    async def delete_by_account_id(self, account_id: str) -> bool:
        """Удалить настройки аккаунта. False, если записи не было."""
        model = await self._get_model(account_id)
        if not model:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    @staticmethod
    def _to_entity(model: IncomeItemSyncConfig) -> IncomeSyncConfig:
        return IncomeSyncConfig(
            id=model.id,
            ms_account_id=model.ms_account_id,
            dictionary_id=model.dictionary_id,
            counterparty_attribute_id=model.counterparty_attribute_id,
            paymentin_attribute_id=model.paymentin_attribute_id,
            cashin_attribute_id=model.cashin_attribute_id,
            enabled=model.enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
