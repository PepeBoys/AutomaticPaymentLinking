"""Основной сервис для работы с вебхуками."""

import logging
from typing import Dict

from src.core.config import settings

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import WebhookOperationResult
from ..domain.value_objects import WebhookConfiguration
from ..exceptions import MissingRequestIdError
from ..schemas import (
    DocumentPriority,
    DocumentType,
    LinkType,
    PaymentType,
    WebhookStatusItem,
)
from ..uow.unit_of_work import UnitOfWork
from .moysklad_client import MoySkladClient
from .webhook_handler import WebhookHandler
from .webhook_operations import WebhookOperationFactory

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Сервис для управления вебхуками.
    
    Координирует работу между API МойСклад и локальной БД.
    """
    
    def __init__(
        self,
        uow: UnitOfWork,
        auth_service: MySkladAuthService,
    ) -> None:
        """
        Инициализировать сервис вебхуков.
        
        Args:
            uow: Unit of Work для работы с БД
            auth_service: Сервис аутентификации МойСклад
        """
        self._uow = uow
        self._auth_service = auth_service
        self._client = MoySkladClient(auth_service)
    
    async def get_webhooks_status(self) -> Dict[str, WebhookStatusItem]:
        """
        Получить статус всех вебхуков с настройками.
        
        Returns:
            Словарь {payment_type: WebhookStatusItem}
        """
        full_status = await self._uow.webhooks.get_full_status_dict()
        
        result = {}
        for payment_type, data in full_status.items():
            result[payment_type] = WebhookStatusItem(
                enabled=data["enabled"],
                document_type=DocumentType(data["document_type"]),
                link_type=LinkType(data["link_type"]),
                document_priority=DocumentPriority(data["document_priority"]),
                payment_purpose_mask=data.get("payment_purpose_mask"),
            )
        
        logger.debug("Статус вебхуков: %s", result)
        return result
    
    async def update_link_settings(
        self,
        payment_type: PaymentType,
        document_type: DocumentType,
        link_type: LinkType,
        document_priority: DocumentPriority,
        payment_purpose_mask: str | None,
    ) -> Dict[str, str]:
        """
        Обновить настройки привязки БЕЗ обращения к МойСклад API.
        
        Args:
            payment_type: Тип платежа
            document_type: Тип документа
            link_type: Тип привязки
            
        Returns:
            Результат операции
        """
        updated = await self._uow.webhooks.update_link_settings(
            payment_type=payment_type,
            document_type=document_type,
            link_type=link_type,
            document_priority=document_priority,
            payment_purpose_mask=payment_purpose_mask,
        )

        if not updated:
            logger.warning(
                "Вебхук %s не найден для обновления настроек",
                payment_type.value,
            )
            return {
                "status": "warning",
                "message": f"Вебхук {payment_type.value} не найден. Включите его сначала.",
            }
        
        await self._uow.commit()
        
        logger.info(
            "Настройки привязки обновлены: payment_type=%s, document_type=%s, link_type=%s",
            payment_type.value,
            document_type.value,
            link_type.value,
        )
        
        return {
            "status": "ok",
            "payment_type": payment_type.value,
            "document_type": document_type.value,
            "link_type": link_type.value,
            "document_priority": document_priority.value,
            "payment_purpose_mask": payment_purpose_mask,
        }
    
    async def toggle_webhook(
        self,
        payment_type: PaymentType,
        enabled: bool,
        document_type: DocumentType = DocumentType.customerorder,
        link_type: LinkType = LinkType.sum_and_counterparty,
        document_priority: DocumentPriority = DocumentPriority.oldest_first,
        payment_purpose_mask: str | None = None,
    ) -> WebhookOperationResult:
        webhook_url = settings.ms_webhook_url
        
        if not webhook_url:
            logger.warning("MS_WEBHOOK_URL не задан")
            return WebhookOperationResult(
                operation="skipped_no_webhook_url",
                success=False,
                message=(
                    "Webhook URL не настроен. Запустите ngrok (DEV_docs/start_ngrok.ps1) "
                    "и перезапустите сервер"
                ),
            )
        
        creds = self._auth_service.get_raw_credentials()
        if not creds:
            logger.warning("МойСклад credentials не настроены")
            return WebhookOperationResult(
                operation="skipped_no_credentials",
                success=False,
                message="MoySklad credentials are not configured",
            )
        
        config = WebhookConfiguration.from_payment_type(
            payment_type=payment_type,
            webhook_url=webhook_url,
        )

        existing_db_entity = await self._uow.webhooks.get_by_payment_type(payment_type)
        
        operation = WebhookOperationFactory.create_operation(
            enabled=enabled,
            client=self._client,
            config=config,
            existing_db_entity=existing_db_entity,
        )
        
        result = await operation.execute()
        
        logger.info(
            "Результат операции: operation=%s, success=%s, has_entity=%s",
            result.operation,
            result.success,
            result.webhook_entity is not None,
        )
        
        if result.success:
            if result.webhook_entity:
                result.webhook_entity.payment_type = payment_type
                result.webhook_entity.document_type = document_type
                result.webhook_entity.link_type = link_type
                result.webhook_entity.document_priority = document_priority
                result.webhook_entity.payment_purpose_mask = payment_purpose_mask
                saved_entity = await self._uow.webhooks.upsert(result.webhook_entity)
                await self._uow.commit()
                
                logger.info(
                    "Webhook сохранен в БД: id=%s, ms_webhook_id=%s, enabled=%s, document_type=%s, link_type=%s",
                    saved_entity.id,
                    saved_entity.ms_webhook_id,
                    saved_entity.enabled,
                    saved_entity.document_type.value,
                    saved_entity.link_type.value,
                )
                
                result.details["db_record_id"] = saved_entity.id
            else:
                existing_db_entity = await self._uow.webhooks.get_by_payment_type(payment_type)
                
                if existing_db_entity:
                    logger.info(
                        "Webhook entity не вернулась из операции, но найдена в БД. "
                        "Обновляем enabled=%s для payment_type=%s",
                        enabled,
                        payment_type.value,
                    )
                    existing_db_entity.enabled = enabled
                    existing_db_entity.document_type = document_type
                    existing_db_entity.link_type = link_type
                    existing_db_entity.document_priority = document_priority
                    existing_db_entity.payment_purpose_mask = payment_purpose_mask
                    saved_entity = await self._uow.webhooks.update(existing_db_entity)
                    await self._uow.commit()
                    
                    logger.info(
                        "Webhook обновлен в БД: id=%s, enabled=%s",
                        saved_entity.id,
                        saved_entity.enabled,
                    )
                    
                    result.details["db_record_id"] = saved_entity.id
                else:
                    logger.warning(
                        "Webhook entity не вернулась из операции и не найдена в БД для payment_type=%s",
                        payment_type.value,
                    )
        
        return result
    
    async def process_incoming_webhook(
        self,
        request_id: str | None,
        payload,
        paymentin_service,
        customerorder_service,
        invoiceout_service,
        demand_service=None,
    ) -> None:
        """
        Обработать входящий webhook от МойСклад.
        
        Args:
            request_id: ID запроса вебхука
            payload: Данные webhook
            paymentin_service: Сервис работы с платежами
            customerorder_service: Сервис работы с заказами
        """
        if not request_id:
            raise MissingRequestIdError("requestId обязателен")
        
        if invoiceout_service is None:
            raise ValueError("InvoiceOutService dependency is required")
        
        if demand_service is None:
            raise ValueError("DemandService dependency is required")

        handler = WebhookHandler(
            paymentin_service,
            customerorder_service,
            invoiceout_service,
            demand_service,
        )
        
        for event in payload.events:
            logger.info(
                "Событие вебхука: type=%s, action=%s, href=%s, accountId=%s, updatedFields=%s",
                event.meta.type,
                event.action,
                event.meta.href,
                event.accountId,
                event.updatedFields,
            )
            
            if event.meta.type == "paymentin" and event.action == "CREATE":
                subscription = await self._uow.webhooks.get_active_subscription_for_event(
                    account_id=event.accountId,
                    entity_type=event.meta.type,
                    payment_type=PaymentType.incoming_payment,
                )
                
                if subscription:
                    result = await handler.handle_paymentin_create(event.meta.href, subscription)
                    logger.info("Результат обработки платежа: success=%s, message=%s", result["success"], result["message"])
                else:
                    logger.warning("Активная подписка не найдена для аккаунта %s и типа %s", event.accountId, event.meta.type)