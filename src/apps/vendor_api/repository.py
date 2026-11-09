from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import VendorAccount, VendorJwtJti


class VendorAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_account_id(self, account_id: str) -> Optional[VendorAccount]:
        stmt = select(VendorAccount).where(VendorAccount.account_id == account_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_account(
        self,
        *,
        account_id: str,
        access_token: str,
        base_url: str | None = None,
        app_uid: str | None = None,
    ) -> VendorAccount:
        account = await self.get_by_account_id(account_id)
        if account:
            account.access_token = access_token
            account.is_active = True
            account.base_url = base_url or account.base_url
            account.app_uid = app_uid or account.app_uid
            await self._session.flush()
            return account

        account = VendorAccount(
            account_id=account_id,
            access_token=access_token,
            base_url=base_url,
            app_uid=app_uid,
        )
        self._session.add(account)
        await self._session.flush()
        return account

    async def update_subscription(
        self, account_id: str, subscription: dict | None
    ) -> Optional[VendorAccount]:
        """Сохранить подписку из МС ({tariffId, tariffName, trial, expiryMoment}).

        subscription=None фиксирует только попытку синхронизации (чтобы не
        запрашивать статус у МС на каждый запрос, если он недоступен).
        """
        account = await self.get_by_account_id(account_id)
        if not account:
            return None

        if subscription:
            account.tariff_id = subscription.get("tariffId")
            account.tariff_name = subscription.get("tariffName")
            account.tariff_trial = subscription.get("trial")
            expiry = subscription.get("expiryMoment")
            account.tariff_expiry = (
                datetime.fromisoformat(expiry.replace("Z", "+00:00")) if expiry else None
            )
        account.subscription_synced_at = datetime.now(UTC)
        await self._session.flush()
        return account

    async def deactivate_account(self, account_id: str) -> Optional[VendorAccount]:
        account = await self.get_by_account_id(account_id)
        if not account:
            return None

        account.is_active = False
        account.access_token = None
        await self._session.flush()
        return account

    async def list_active_accounts(self, *, limit: int | None = None) -> list[VendorAccount]:
        stmt = select(VendorAccount).where(VendorAccount.is_active.is_(True))

        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class VendorJtiRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_used(self, jti: str) -> bool:
        stmt = select(VendorJwtJti).where(VendorJwtJti.jti == jti)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def save(self, *, jti: str, expires_at: datetime) -> VendorJwtJti:
        record = VendorJwtJti(jti=jti, expires_at=expires_at)
        self._session.add(record)
        await self._session.flush()
        return record

    async def cleanup_expired(self, now: datetime) -> None:
        stmt = delete(VendorJwtJti).where(VendorJwtJti.expires_at < now)
        await self._session.execute(stmt)