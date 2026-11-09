"""Определение доступных функций по тарифу аккаунта.

Правила:
- тарифы не настроены (APL_TARIFF_FEATURES пуст) — доступно всё;
- тариф аккаунта неизвестен (МС его ещё не прислал и запрос статуса не удался) —
  доступно всё, чтобы сбой не отключил функции у платящих клиентов;
- тариф есть в настройках — доступны его функции (на триале — те же);
- тариф известен, но не настроен — платные функции недоступны.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings

from ..vendor_api.repository import VendorAccountRepository
from .constants import FEATURE_LABELS, SUBSCRIPTION_SYNC_RETRY_SECONDS
from .status_client import fetch_subscription

logger = logging.getLogger(__name__)


@dataclass
class AccountTariff:
    tariffs_enabled: bool
    known: bool
    tariff_id: Optional[str] = None
    tariff_name: Optional[str] = None
    trial: Optional[bool] = None
    expiry: Optional[datetime] = None
    features: frozenset[str] = field(default_factory=frozenset)


class TariffService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._accounts = VendorAccountRepository(session)

    @staticmethod
    def tariffs_enabled() -> bool:
        return bool(settings.tariff_features)

    async def get_account_tariff(self, account_id: str) -> AccountTariff:
        all_features = frozenset(FEATURE_LABELS)
        if not self.tariffs_enabled():
            return AccountTariff(tariffs_enabled=False, known=False, features=all_features)

        account = await self._accounts.get_by_account_id(account_id)
        if account and not account.tariff_id and self._sync_due(account.subscription_synced_at):
            subscription = await fetch_subscription(account_id)
            account = await self._accounts.update_subscription(account_id, subscription)
            await self._session.commit()

        if not account or not account.tariff_id:
            logger.warning(
                "Тариф аккаунта %s неизвестен, функции не ограничиваются", account_id
            )
            return AccountTariff(tariffs_enabled=True, known=False, features=all_features)

        tariff_config = settings.tariff_features.get(account.tariff_id) or {}
        features = frozenset(tariff_config.get("features", [])) & all_features
        return AccountTariff(
            tariffs_enabled=True,
            known=True,
            tariff_id=account.tariff_id,
            tariff_name=account.tariff_name or tariff_config.get("name"),
            trial=account.tariff_trial,
            expiry=account.tariff_expiry,
            features=features,
        )

    async def has_feature(self, account_id: str, feature: str) -> bool:
        tariff = await self.get_account_tariff(account_id)
        return feature in tariff.features

    @staticmethod
    def required_tariff_names(feature: str) -> list[str]:
        """Названия тарифов из настроек, в которые входит функция."""
        return [
            cfg.get("name") or tariff_id
            for tariff_id, cfg in settings.tariff_features.items()
            if feature in cfg.get("features", [])
        ]

    @classmethod
    def locked_message(cls, feature: str) -> str:
        label = FEATURE_LABELS.get(feature, feature)
        names = cls.required_tariff_names(feature)
        if names:
            return f"«{label}» доступно в тарифе: " + ", ".join(f"«{n}»" for n in names)
        return f"«{label}» недоступно в вашем тарифе"

    @staticmethod
    def _sync_due(synced_at: Optional[datetime]) -> bool:
        if synced_at is None:
            return True
        if synced_at.tzinfo is None:  # SQLite возвращает время без зоны
            synced_at = synced_at.replace(tzinfo=UTC)
        return datetime.now(UTC) - synced_at > timedelta(
            seconds=SUBSCRIPTION_SYNC_RETRY_SECONDS
        )
