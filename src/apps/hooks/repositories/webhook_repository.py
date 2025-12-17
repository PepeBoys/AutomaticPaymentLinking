"""Репозиторий для работы с вебхуками."""

from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.entities import WebhookEntity
from ..exceptions import RepositoryError
from ..models import WebhookSubscription
from ..schemas import DocumentPriority, DocumentType, LinkType, PaymentType
from .base import AbstractRepository


class WebhookRepository(AbstractRepository[WebhookEntity]):
    """Репозиторий для управления вебхуками."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализировать репозиторий вебхуков.
        
        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session)

    async def get_by_id(self, entity_id: int) -> Optional[WebhookEntity]:
        """
        Получить вебхук по ID.

        Args:
            entity_id: ID вебхука
            
        Returns:
            Сущность вебхука или None
        """
        stmt = select(WebhookSubscription).where(WebhookSubscription.id == entity_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._to_entity(model) if model else None
    
    async def get_all(self) -> List[WebhookEntity]:
        """
        Получить все вебхуки.
        
        Returns:
            Список сущностей вебхуков
        """
        stmt = select(WebhookSubscription)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._to_entity(model) for model in models]
    
    async def get_by_ms_webhook_id(self, ms_webhook_id: str) -> Optional[WebhookEntity]:
        """
        Получить вебхук по ID МойСклад.
        
        Args:
            ms_webhook_id: ID вебхука в МойСклад
            
        Returns:
            Сущность вебхука или None
        """
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.ms_webhook_id == ms_webhook_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._to_entity(model) if model else None
    
    async def get_by_payment_type(self, payment_type: PaymentType) -> Optional[WebhookEntity]:
        """
        Получить вебхук по типу платежа.
        
        Args:
            payment_type: Тип платежа
            
        Returns:
            Сущность вебхука или None
        """
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.payment_type == payment_type
        ).order_by(WebhookSubscription.id.desc())
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        
        return self._to_entity(model) if model else None
    
    async def get_active_subscription_for_event(
        self,
        account_id: str,
        entity_type: str,
        payment_type: PaymentType,
    ) -> Optional[WebhookEntity]:
        """
        Получить активную подписку для обработки события.
        
        Args:
            account_id: ID аккаунта МойСклад
            entity_type: Тип сущности
            payment_type: Тип платежа
            
        Returns:
            Активная подписка или None
        """
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.ms_account_id == account_id,
            WebhookSubscription.entity_type == entity_type,
            WebhookSubscription.payment_type == payment_type,
            WebhookSubscription.enabled == True,
        ).order_by(WebhookSubscription.id.desc())
        
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        
        return self._to_entity(model) if model else None
    
    async def update_link_settings(
        self,
        payment_type: PaymentType,
        document_type: DocumentType,
        link_type: LinkType,
        document_priority: DocumentPriority,
        payment_purpose_mask: str | None,
        payment_status_on_success: str | None,
        payment_status_on_failure: str | None,
        document_status_on_success: str | None,
        transfer_project_to_payment: bool,
        check_document_organization: bool,
    ) -> Optional[WebhookEntity]:
        """
        Обновить настройки привязки для существующего вебхука.
        
        Args:
            payment_type: Тип платежа
            document_type: Тип документа
            link_type: Тип привязки
            
        Returns:
            Обновленная сущность или None если вебхук не найден
        """
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.payment_type == payment_type,
            WebhookSubscription.enabled == True,
        ).order_by(WebhookSubscription.id.desc())
        result = await self._session.execute(stmt)
        model = result.scalars().first()

        if not model:
            return None

        model.document_type = document_type
        model.link_type = link_type
        model.document_priority = document_priority
        model.payment_purpose_mask = payment_purpose_mask
        model.payment_status_on_success = payment_status_on_success
        model.payment_status_on_failure = payment_status_on_failure
        model.document_status_on_success = document_status_on_success
        model.transfer_project_to_payment = transfer_project_to_payment
        model.check_document_organization = check_document_organization

        await self._session.flush()
        await self._session.refresh(model)
        
        return self._to_entity(model)

    async def get_status_dict(self) -> Dict[str, bool]:
        """
        Получить словарь статусов всех вебхуков.

        Returns:
            Словарь {payment_type: enabled}
        """
        webhooks = await self.get_all()
        return {webhook.payment_type.value: webhook.enabled for webhook in webhooks}

    async def get_full_status_dict(self) -> Dict[str, Dict[str, str]]:
        """
        Получить полный словарь статусов всех вебхуков с настройками.
        
        Returns:
            Словарь {payment_type: {enabled, document_type, link_type}}
        """
        all_payment_types = [
            PaymentType.incoming_payment,
            PaymentType.incoming_order,
            PaymentType.outgoing_payment,
            PaymentType.outgoing_order,
        ]
        
        result = {}
        
        for pt in all_payment_types:
            stmt = select(WebhookSubscription).where(
                WebhookSubscription.payment_type == pt
            ).order_by(WebhookSubscription.id.desc())
            query_result = await self._session.execute(stmt)
            model = query_result.scalars().first()
            
            if model:
                result[pt.value] = {
                    "enabled": model.enabled,
                    "document_type": model.document_type.value,
                    "link_type": model.link_type.value,
                    "document_priority": model.document_priority.value,
                    "payment_purpose_mask": model.payment_purpose_mask,
                    "payment_status_on_success": model.payment_status_on_success,
                    "payment_status_on_failure": model.payment_status_on_failure,
                    "document_status_on_success": model.document_status_on_success,
                    "transfer_project_to_payment": model.transfer_project_to_payment,
                    "check_document_organization": model.check_document_organization,
                }
            else:
                result[pt.value] = {
                    "enabled": False,
                    "document_type": DocumentType.customerorder.value,
                    "link_type": LinkType.sum_and_counterparty.value,
                    "document_priority": DocumentPriority.oldest_first.value,
                    "payment_purpose_mask": None,
                    "payment_status_on_success": None,
                    "payment_status_on_failure": None,
                    "document_status_on_success": None,
                    "transfer_project_to_payment": False,
                    "check_document_organization": False,
                }

        return result

    async def add(self, entity: WebhookEntity) -> WebhookEntity:
        """
        Добавить новый вебхук.

        Args:
            entity: Сущность вебхука

        Returns:
            Добавленная сущность

        Raises:
            RepositoryError: При ошибке добавления
        """
        try:
            model = self._to_model(entity)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            return self._to_entity(model)
        except Exception as exc:
            raise RepositoryError(
                "Ошибка при добавлении вебхука",
                details={"error": str(exc)},
            ) from exc

    async def update(self, entity: WebhookEntity) -> WebhookEntity:
        """
        Обновить существующий вебхук.

        Args:
            entity: Сущность вебхука

        Returns:
            Обновленная сущность

        Raises:
            RepositoryError: При ошибке обновления
        """
        try:
            stmt = select(WebhookSubscription).where(
                WebhookSubscription.ms_webhook_id == entity.ms_webhook_id
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                raise RepositoryError(
                    f"Вебхук с ms_webhook_id={entity.ms_webhook_id} не найден"
                )

            model.payment_type = entity.payment_type
            model.entity_type = entity.entity_type
            model.action = entity.action
            model.url = entity.url
            model.ms_href = entity.ms_href
            model.ms_account_id = entity.ms_account_id
            model.enabled = entity.enabled
            model.document_type = entity.document_type
            model.link_type = entity.link_type
            model.document_priority = entity.document_priority
            model.payment_purpose_mask = entity.payment_purpose_mask
            model.payment_status_on_success = entity.payment_status_on_success
            model.payment_status_on_failure = entity.payment_status_on_failure
            model.document_status_on_success = entity.document_status_on_success
            model.transfer_project_to_payment = entity.transfer_project_to_payment
            model.check_document_organization = entity.check_document_organization

            await self._session.flush()
            await self._session.refresh(model)
            return self._to_entity(model)
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError(
                "Ошибка при обновлении вебхука",
                details={"error": str(exc)},
            ) from exc
    
    async def upsert(self, entity: WebhookEntity) -> WebhookEntity:
        """
        Создать или обновить вебхук.
        
        Args:
            entity: Сущность вебхука
            
        Returns:
            Сущность вебхука
        """
        existing = await self.get_by_ms_webhook_id(entity.ms_webhook_id)
        
        if existing:
            entity.id = existing.id
            return await self.update(entity)
        else:
            return await self.add(entity)
    
    async def delete(self, entity_id: int) -> None:
        """
        Удалить вебхук по ID.
        
        Args:
            entity_id: ID вебхука
            
        Raises:
            RepositoryError: При ошибке удаления
        """
        try:
            stmt = select(WebhookSubscription).where(WebhookSubscription.id == entity_id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if model:
                await self._session.delete(model)
                await self._session.flush()
        except Exception as exc:
            raise RepositoryError(
                "Ошибка при удалении вебхука",
                details={"error": str(exc)},
            ) from exc
    
    @staticmethod
    def _to_entity(model: WebhookSubscription) -> WebhookEntity:
        """
        Преобразовать модель БД в доменную сущность.
        
        Args:
            model: Модель SQLAlchemy
            
        Returns:
            Доменная сущность
        """
        return WebhookEntity(
            id=model.id,
            payment_type=model.payment_type,
            entity_type=model.entity_type,
            action=model.action,
            url=model.url,
            ms_webhook_id=model.ms_webhook_id,
            ms_href=model.ms_href,
            ms_account_id=model.ms_account_id,
            enabled=model.enabled,
            document_type=model.document_type,
            link_type=model.link_type,
            document_priority=model.document_priority,
            payment_purpose_mask=model.payment_purpose_mask,
            payment_status_on_success=model.payment_status_on_success,
            payment_status_on_failure=model.payment_status_on_failure,
            document_status_on_success=model.document_status_on_success,
            transfer_project_to_payment=model.transfer_project_to_payment,
            check_document_organization=model.check_document_organization,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_model(entity: WebhookEntity) -> WebhookSubscription:
        """
        Преобразовать доменную сущность в модель БД.

        Args:
            entity: Доменная сущность

        Returns:
            Модель SQLAlchemy
        """
        return WebhookSubscription(
            id=entity.id,
            payment_type=entity.payment_type,
            entity_type=entity.entity_type,
            action=entity.action,
            url=entity.url,
            ms_webhook_id=entity.ms_webhook_id,
            ms_href=entity.ms_href,
            ms_account_id=entity.ms_account_id,
            enabled=entity.enabled,
            document_type=entity.document_type,
            link_type=entity.link_type,
            document_priority=entity.document_priority,
            payment_purpose_mask=entity.payment_purpose_mask,
            payment_status_on_success=entity.payment_status_on_success,
            payment_status_on_failure=entity.payment_status_on_failure,
            document_status_on_success=entity.document_status_on_success,
            transfer_project_to_payment=entity.transfer_project_to_payment,
            check_document_organization=entity.check_document_organization,
        )