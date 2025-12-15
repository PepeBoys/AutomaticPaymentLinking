import logging

from fastapi import APIRouter, Response

from ..customerorder.dependencies import CustomerOrderSvcDep
from ..demand.dependencies import DemandSvcDep
from ..invoiceout.dependencies import InvoiceOutSvcDep
from ..paymentin.dependencies import PaymentInSvcDep
from .dependencies import RequestIdQuery, WebhookSvcDep
from .schemas import (
    AutoLinkTogglePayload,
    MySkladWebhookPayload,
    PaymentType,
    UpdateLinkSettingsPayload,
    WebhookStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhooks/status", response_model=WebhookStatusResponse)
async def get_webhooks_status(service: WebhookSvcDep):
    status_dict = await service.get_webhooks_status()
    return WebhookStatusResponse(webhooks=status_dict)


@router.post("/update-link-settings")
async def update_link_settings(
    payload: UpdateLinkSettingsPayload,
    service: WebhookSvcDep,
):
    logger.info(
        "Обновление настроек привязки: payment_type=%s, document_type=%s, link_type=%s, priority=%s, mask=%s",
        payload.payment_type,
        payload.document_type,
        payload.link_type,
        payload.document_priority,
        payload.payment_purpose_mask,
    )

    result = await service.update_link_settings(
        payment_type=payload.payment_type,
        document_type=payload.document_type,
        link_type=payload.link_type,
        document_priority=payload.document_priority,
        payment_purpose_mask=payload.payment_purpose_mask,
    )

    return result


@router.post("/auto-link-toggle")
async def auto_link_toggle(payload: AutoLinkTogglePayload, service: WebhookSvcDep):
    logger.info(
        "UI toggle: payment_type=%s, enabled=%s, document_type=%s, link_type=%s, priority=%s, mask=%s",
        payload.payment_type,
        payload.enabled,
        payload.document_type,
        payload.link_type,
        payload.document_priority,
        payload.payment_purpose_mask,
    )

    result = await service.toggle_webhook(
        payment_type=payload.payment_type,
        enabled=payload.enabled,
        document_type=payload.document_type,
        link_type=payload.link_type,
        document_priority=payload.document_priority,
        payment_purpose_mask=payload.payment_purpose_mask,
    )
   
    if result.is_skipped():
        return {
            "status": "warning",
            "payment_type": payload.payment_type,
            "enabled": payload.enabled,
            "operation": result.operation,
            "message": result.message or "Операция пропущена",
        }

    return {
        "status": "ok",
        "payment_type": payload.payment_type,
        "enabled": payload.enabled,
        "operation": result.operation,
        "db_record_id": result.details.get("db_record_id"),
    }


@router.post("/moysklad/webhook", status_code=204)
async def receive_moysklad_webhook(
    payload: MySkladWebhookPayload,
    service: WebhookSvcDep,
    paymentin_service: PaymentInSvcDep,
    customerorder_service: CustomerOrderSvcDep,
    invoiceout_service: InvoiceOutSvcDep,
    demand_service: DemandSvcDep,
    request_id: RequestIdQuery = None,
) -> Response:
    logger.info(
        "Получен вебхук МойСклад: requestId=%s, events=%d, uid=%s, moment=%s",
        request_id,
        len(payload.events),
        payload.auditContext.uid,
        payload.auditContext.moment,
    )

    await service.process_incoming_webhook(
        request_id=request_id,
        payload=payload,
        paymentin_service=paymentin_service,
        customerorder_service=customerorder_service,
        invoiceout_service=invoiceout_service,
        demand_service=demand_service,
    )

    return Response(status_code=204)