"""Основной сервис для работы с вебхуками."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

from src.core.config import settings

from ...ms_auth.services.auth_service import MySkladAuthService
from sqlalchemy.exc import IntegrityError

from ..domain.entities import WebhookOperationResult
from ..domain.value_objects import WebhookConfiguration
from ..exceptions import MissingRequestIdError, WebhookConfigurationError
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

    def _require_account_id(self) -> str:
        account_id = self._auth_service.get_account_id()

        if not account_id:
            raise WebhookConfigurationError(
                "AccountId не найден. Активируйте приложение через Vendor API"
            )

        return account_id
    
    async def cleanup_account_webhooks(self, account_id: str) -> dict[str, int]:
        """
        Удалить все вебхуки аккаунта из МойСклад и БД.
        
        Args:
            account_id: ID аккаунта
            
        Returns:
            Словарь со статистикой удаления
        """
        webhooks = await self._uow.webhooks.get_all(account_id)
        
        deleted_from_ms = 0
        failed_to_delete_from_ms = 0
        not_found_in_ms = 0
        
        for webhook in webhooks:
            if webhook.ms_webhook_id:
                try:
                    success = await self._client.delete_webhook(webhook.ms_webhook_id)
                    if success:
                        deleted_from_ms += 1
                    else:
                        not_found_in_ms += 1
                except Exception as exc:
                    logger.error(
                        "Ошибка при удалении вебхука из МойСклад: webhook_id=%s, error=%s, type=%s",
                        webhook.ms_webhook_id,
                        exc,
                        type(exc).__name__,
                        exc_info=True,
                    )
                    failed_to_delete_from_ms += 1
        
        deleted_from_db = await self._uow.webhooks.delete_all_by_account_id(account_id)
        await self._uow.commit()
        logger.info("Удалено из БД: %d записей для account_id=%s", deleted_from_db, account_id)
         
        
        return {
            "deleted_from_ms": deleted_from_ms,
            "not_found_in_ms": not_found_in_ms,
            "failed_to_delete_from_ms": failed_to_delete_from_ms,
            "deleted_from_db": deleted_from_db,
        }
    
    async def get_webhooks_status(self) -> Dict[str, WebhookStatusItem]:
        """
        Получить статус всех вебхуков с настройками.

        Returns:
            Словарь {payment_type: WebhookStatusItem}
        """
        account_id = self._require_account_id()
        full_status = await self._uow.webhooks.get_full_status_dict(account_id)
        
        result = {}
        for payment_type, data in full_status.items():
            result[payment_type] = WebhookStatusItem(
                enabled=data["enabled"],
                document_type=DocumentType(data["document_type"]),
                link_type=LinkType(data["link_type"]),
                document_priority=DocumentPriority(data["document_priority"]),
                payment_purpose_mask=data.get("payment_purpose_mask"),
                payment_status_on_success=data.get("payment_status_on_success"),
                payment_status_on_failure=data.get("payment_status_on_failure"),
                document_status_on_success=data.get("document_status_on_success"),
                transfer_project_to_payment=data.get(
                    "transfer_project_to_payment", False
                ),
                transfer_sales_channel_to_payment=data.get(
                    "transfer_sales_channel_to_payment", False
                ),
                check_document_organization=data.get(
                    "check_document_organization", False
                ),
            )

        logger.debug("Статус вебхуков для account_id=%s: %s", account_id, result)
        return result

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
        transfer_sales_channel_to_payment: bool,
        check_document_organization: bool,
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
        account_id = self._require_account_id()
        updated = await self._uow.webhooks.update_link_settings(
            payment_type=payment_type,
            document_type=document_type,
            link_type=link_type,
            document_priority=document_priority,
            payment_purpose_mask=payment_purpose_mask,
            payment_status_on_success=payment_status_on_success,
            payment_status_on_failure=payment_status_on_failure,
            document_status_on_success=document_status_on_success,
            transfer_project_to_payment=transfer_project_to_payment,
            transfer_sales_channel_to_payment=transfer_sales_channel_to_payment,
            check_document_organization=check_document_organization,
            account_id=account_id,
        )

        if not updated:
            logger.warning(
                "Вебхук %s не найден для обновления настроек в account_id=%s",
                payment_type.value,
                account_id,
            )
            return {
                "status": "warning",
                "message": f"Вебхук {payment_type.value} не найден. Включите его сначала.",
            }
        
        await self._uow.commit()
        
        logger.info(
            "Настройки привязки обновлены: account_id=%s, payment_type=%s, document_type=%s, link_type=%s",
            account_id,
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
            "payment_status_on_success": payment_status_on_success,
            "payment_status_on_failure": payment_status_on_failure,
            "document_status_on_success": document_status_on_success,
            "transfer_project_to_payment": transfer_project_to_payment,
            "transfer_sales_channel_to_payment": transfer_sales_channel_to_payment,
            "check_document_organization": check_document_organization,
        }

    async def toggle_webhook(
        self,
        payment_type: PaymentType,
        enabled: bool,
        document_type: DocumentType = DocumentType.customerorder,
        link_type: LinkType = LinkType.sum_and_counterparty,
        document_priority: DocumentPriority = DocumentPriority.oldest_first,
        payment_purpose_mask: str | None = None,
        payment_status_on_success: str | None = None,
        payment_status_on_failure: str | None = None,
        document_status_on_success: str | None = None,
        transfer_project_to_payment: bool = False,
        transfer_sales_channel_to_payment: bool = False,
        check_document_organization: bool = False,
    ) -> WebhookOperationResult:
        account_id = self._require_account_id()
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

        existing_db_entity = await self._uow.webhooks.get_by_payment_type(
            payment_type, account_id
        )
        logger.info("existing_db_entity для %s: %s", payment_type.value, existing_db_entity)
        
        operation = WebhookOperationFactory.create_operation(
            enabled=enabled,
            client=self._client,
            config=config,
            existing_db_entity=existing_db_entity,
        )

        result = await operation.execute()

        logger.info(
            "Результат операции: account_id=%s, operation=%s, success=%s, has_entity=%s",
            account_id,
            result.operation,
            result.success,
            result.webhook_entity is not None,
        )

        if result.success:
            if result.webhook_entity:
                if not result.webhook_entity.ms_account_id:
                    result.webhook_entity.ms_account_id = account_id

                result.webhook_entity.payment_type = payment_type
                result.webhook_entity.document_type = document_type
                result.webhook_entity.link_type = link_type
                result.webhook_entity.document_priority = document_priority
                result.webhook_entity.payment_purpose_mask = payment_purpose_mask
                result.webhook_entity.payment_status_on_success = payment_status_on_success
                result.webhook_entity.payment_status_on_failure = payment_status_on_failure
                result.webhook_entity.document_status_on_success = document_status_on_success
                result.webhook_entity.transfer_project_to_payment = (
                    transfer_project_to_payment
                )
                result.webhook_entity.transfer_sales_channel_to_payment = (
                    transfer_sales_channel_to_payment
                )
                result.webhook_entity.check_document_organization = (
                    check_document_organization
                )
                try:
                    saved_entity = await self._uow.webhooks.upsert(result.webhook_entity)
                except Exception as exc:
                    logger.error(
                        "Ошибка при upsert вебхука: account_id=%s, payment_type=%s, ms_webhook_id=%s, error=%s",
                        account_id, payment_type.value, result.webhook_entity.ms_webhook_id, exc
                    )
                    raise
                await self._uow.commit()

                logger.info(
                    "Webhook сохранен в БД: account_id=%s, id=%s, ms_webhook_id=%s, enabled=%s, document_type=%s, link_type=%s",
                    account_id,
                    saved_entity.id,
                    saved_entity.ms_webhook_id,
                    saved_entity.enabled,
                    saved_entity.document_type.value,
                    saved_entity.link_type.value,
                )

                result.details["db_record_id"] = saved_entity.id
            else:
                existing_db_entity = await self._uow.webhooks.get_by_payment_type(
                    payment_type, account_id
                )

                if existing_db_entity:
                    logger.info(
                        "Webhook entity не вернулась из операции, но найдена в БД. "
                        "Обновляем enabled=%s для account_id=%s, payment_type=%s",
                        enabled,
                        account_id,
                        payment_type.value,
                    )
                    existing_db_entity.enabled = enabled
                    existing_db_entity.document_type = document_type
                    existing_db_entity.link_type = link_type
                    existing_db_entity.document_priority = document_priority
                    existing_db_entity.payment_purpose_mask = payment_purpose_mask
                    existing_db_entity.payment_status_on_success = payment_status_on_success
                    existing_db_entity.payment_status_on_failure = payment_status_on_failure
                    existing_db_entity.document_status_on_success = document_status_on_success
                    existing_db_entity.transfer_project_to_payment = (
                        transfer_project_to_payment
                    )
                    existing_db_entity.transfer_sales_channel_to_payment = (
                        transfer_sales_channel_to_payment
                    )
                    existing_db_entity.check_document_organization = (
                        check_document_organization
                    )
                    saved_entity = await self._uow.webhooks.update(existing_db_entity)
                    await self._uow.commit()

                    logger.info(
                        "Webhook обновлен в БД: account_id=%s, id=%s, enabled=%s",
                        account_id,
                        saved_entity.id,
                        saved_entity.enabled,
                    )

                    result.details["db_record_id"] = saved_entity.id
                else:
                    logger.warning(
                        "Webhook entity не вернулась из операции и не найдена в БД для account_id=%s, payment_type=%s",
                        account_id,
                        payment_type.value,
                    )

        return result

    async def process_incoming_webhook(
        self,
        request_id: str | None,
        payload,
        paymentin_service,
        cashin_service,
        paymentout_service,
        cashout_service,
        customerorder_service,
        invoiceout_service,
        demand_service=None,
        purchaseorder_service=None,
        invoicein_service=None,
        supply_service=None,
    ) -> None:
        """
        Обработать входящий webhook от МойСклад.

        Args:
            request_id: ID запроса вебхука
            payload: Данные webhook
            paymentin_service: Сервис работы с платежами
            cashin_service: Сервис работы с приходными ордерами
            customerorder_service: Сервис работы с заказами
        """
        if not request_id:
            raise MissingRequestIdError("requestId обязателен")

        if invoiceout_service is None:
            raise ValueError("InvoiceOutService dependency is required")

        if demand_service is None:
            raise ValueError("DemandService dependency is required")

        if cashin_service is None:
            raise ValueError("CashInService dependency is required")

        if paymentout_service is None:
            raise ValueError("PaymentOutService dependency is required")

        if cashout_service is None:
            raise ValueError("CashOutService dependency is required")

        if purchaseorder_service is None:
            raise ValueError("PurchaseOrderService dependency is required")

        if invoicein_service is None:
            raise ValueError("InvoiceInService dependency is required")

        if supply_service is None:
            raise ValueError("SupplyService dependency is required")

        handler = WebhookHandler(
            paymentin_service,
            cashin_service,
            paymentout_service,
            cashout_service,
            customerorder_service,
            invoiceout_service,
            demand_service,
            purchaseorder_service,
            invoicein_service,
            supply_service,
        )
        
        for event in payload.events:
            logger.info(
                "Событие вебхука: accountId=%s, type=%s, action=%s, href=%s, updatedFields=%s",
                event.accountId,
                event.meta.type,
                event.action,
                event.meta.href,
                event.updatedFields,
            )

            if event.meta.type == "paymentin" and event.action == "CREATE":
                subscription = await self._uow.webhooks.get_active_subscription_for_event(
                    account_id=event.accountId,
                    entity_type=event.meta.type,
                    payment_type=PaymentType.incoming_payment,
                )

                if subscription:
                    if subscription.ms_account_id != event.accountId:
                        logger.error(
                            "КРИТИЧЕСКАЯ ОШИБКА: Несоответствие account_id! "
                            "subscription.ms_account_id=%s, event.accountId=%s",
                            subscription.ms_account_id,
                            event.accountId,
                        )
                        continue

                    result = await handler.handle_paymentin_create(event.meta.href, subscription)
                    logger.info("Результат обработки платежа: success=%s, message=%s", result["success"], result["message"])
                else:
                    logger.warning("Активная подписка не найдена для аккаунта %s и типа %s", event.accountId, event.meta.type)
            elif event.meta.type == "cashin" and event.action == "CREATE":
                subscription = await self._uow.webhooks.get_active_subscription_for_event(
                    account_id=event.accountId,
                    entity_type=event.meta.type,
                    payment_type=PaymentType.incoming_order,
                )

                if subscription:
                    if subscription.ms_account_id != event.accountId:
                        logger.error(
                            "КРИТИЧЕСКАЯ ОШИБКА: Несоответствие account_id! "
                            "subscription.ms_account_id=%s, event.accountId=%s",
                            subscription.ms_account_id,
                            event.accountId,
                        )
                        continue

                    result = await handler.handle_cashin_create(event.meta.href, subscription)
                    logger.info(
                        "Результат обработки приходного ордера: success=%s, message=%s",
                        result["success"],
                        result["message"],
                    )
                else:
                    logger.warning(
                        "Активная подписка не найдена для аккаунта %s и типа %s",
                        event.accountId,
                        event.meta.type,
                    )
            elif event.meta.type == "paymentout" and event.action == "CREATE":
                subscription = await self._uow.webhooks.get_active_subscription_for_event(
                    account_id=event.accountId,
                    entity_type=event.meta.type,
                    payment_type=PaymentType.outgoing_payment,
                )

                if subscription:
                    if subscription.ms_account_id != event.accountId:
                        logger.error(
                            "КРИТИЧЕСКАЯ ОШИБКА: Несоответствие account_id! "
                            "subscription.ms_account_id=%s, event.accountId=%s",
                            subscription.ms_account_id,
                            event.accountId,
                        )
                        continue

                    result = await handler.handle_paymentout_create(
                        event.meta.href, subscription
                    )
                    logger.info(
                        "Результат обработки исходящего платежа: success=%s, message=%s",
                        result["success"],
                        result["message"],
                    )
                else:
                    logger.warning(
                        "Активная подписка не найдена для аккаунта %s и типа %s",
                        event.accountId,
                        event.meta.type,
                    )
            elif event.meta.type == "cashout" and event.action == "CREATE":
                subscription = await self._uow.webhooks.get_active_subscription_for_event(
                    account_id=event.accountId,
                    entity_type=event.meta.type,
                    payment_type=PaymentType.outgoing_order,
                )

                if subscription:
                    if subscription.ms_account_id != event.accountId:
                        logger.error(
                            "КРИТИЧЕСКАЯ ОШИБКА: Несоответствие account_id! "
                            "subscription.ms_account_id=%s, event.accountId=%s",
                            subscription.ms_account_id,
                            event.accountId,
                        )
                        continue

                    result = await handler.handle_cashout_create(
                        event.meta.href, subscription
                    )
                    logger.info(
                        "Результат обработки расходного ордера: success=%s, message=%s",
                        result["success"],
                        result["message"],
                    )
                else:
                    logger.warning(
                        "Активная подписка не найдена для аккаунта %s и типа %s",
                        event.accountId,
                        event.meta.type,
                    )

    async def register_webhook_request(
        self,
        *,
        request_id: str,
        account_id: str | None,
        events_count: int,
    ) -> str:
        now = datetime.now(timezone.utc)
        await self._uow.webhook_requests.cleanup_expired(now)
        existing = await self._uow.webhook_requests.get_by_request_id(request_id)

        if existing and existing.expires_at >= now:
            return "duplicate"

        if existing:
            await self._uow.webhook_requests.delete_by_request_id(request_id)

        expires_at = now + timedelta(seconds=settings.webhook_request_ttl_seconds)
        try:
            await self._uow.webhook_requests.save(
                request_id=request_id,
                account_id=account_id,
                events_count=events_count,
                status="accepted",
                expires_at=expires_at,
            )
            await self._uow.commit()
        except IntegrityError:
            await self._uow.rollback()
            return "duplicate"
        except Exception:
            await self._uow.rollback()
            raise

        return "accepted"
