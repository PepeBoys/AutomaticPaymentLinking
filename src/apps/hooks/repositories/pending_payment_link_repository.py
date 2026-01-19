"""Репозиторий для отслеживания pending привязок платежей к документам."""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PendingPaymentLink


class PendingPaymentLinkRepository:
    """Репозиторий для управления временными pending привязками."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_pending_sum_for_document(
        self, account_id: str, document_id: str
    ) -> float:
        """
        Получить сумму всех pending привязок для документа.
        
        Args:
            account_id: ID аккаунта МойСклад
            document_id: ID документа
            
        Returns:
            Общая сумма pending привязок
        """
        now = datetime.now(timezone.utc)
        stmt = select(PendingPaymentLink).where(
            PendingPaymentLink.account_id == account_id,
            PendingPaymentLink.document_id == document_id,
            PendingPaymentLink.expires_at > now,
        )
        result = await self._session.execute(stmt)
        links = result.scalars().all()
        return sum(link.linked_sum for link in links)

    async def add_pending_link(
        self,
        *,
        account_id: str,
        document_id: str,
        payment_id: str,
        linked_sum: float,
        expires_at: datetime,
    ) -> None:
        """
        Добавить pending привязку.
        
        Args:
            account_id: ID аккаунта МойСклад
            document_id: ID документа
            payment_id: ID платежа
            linked_sum: Сумма привязки
            expires_at: Время истечения
        """
        link = PendingPaymentLink(
            account_id=account_id,
            document_id=document_id,
            payment_id=payment_id,
            linked_sum=linked_sum,
            expires_at=expires_at,
        )
        self._session.add(link)
        await self._session.flush()

    async def cleanup_expired(self, now: datetime) -> None:
        """
        Удалить истекшие pending привязки.
        
        Args:
            now: Текущее время
        """
        stmt = delete(PendingPaymentLink).where(PendingPaymentLink.expires_at < now)
        await self._session.execute(stmt)

    async def delete_by_payment_id(self, payment_id: str) -> None:
        """
        Удалить все pending привязки для конкретного платежа.
        
        Args:
            payment_id: ID платежа
        """
        stmt = delete(PendingPaymentLink).where(
            PendingPaymentLink.payment_id == payment_id
        )
        await self._session.execute(stmt)

    async def get_all_for_account(self, account_id: str) -> List[PendingPaymentLink]:
        """
        Получить все активные pending привязки для аккаунта.
        
        Args:
            account_id: ID аккаунта МойСклад
            
        Returns:
            Список pending привязок
        """
        now = datetime.now(timezone.utc)
        stmt = select(PendingPaymentLink).where(
            PendingPaymentLink.account_id == account_id,
            PendingPaymentLink.expires_at > now,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
