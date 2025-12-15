import logging

from fastapi import APIRouter, HTTPException, Response

from ..cashin.dependencies import CashInSvcDep
from ..customerorder.dependencies import CustomerOrderSvcDep
from ..demand.dependencies import DemandSvcDep
from ..invoiceout.dependencies import InvoiceOutSvcDep
from ..paymentin.dependencies import PaymentInSvcDep
from .dependencies import RequestIdQuery, WebhookSvcDep
from .schemas import (
    AutoLinkTogglePayload,
    DocumentType,
    MySkladWebhookPayload,
    PaymentType,
    StatesResponse,
    UpdateLinkSettingsPayload,
    WebhookStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhooks/status", response_model=WebhookStatusResponse)
async def get_webhooks_status(service: WebhookSvcDep):
    status_dict = await service.get_webhooks_status()
    return WebhookStatusResponse(webhooks=status_dict)


@router.get("/statuses", response_model=StatesResponse)
async def get_states(
    payment_type: PaymentType,
    document_type: DocumentType = DocumentType.customerorder,
    paymentin_service: PaymentInSvcDep = None,
    cashin_service: CashInSvcDep = None,
    customerorder_service: CustomerOrderSvcDep = None,
    invoiceout_service: InvoiceOutSvcDep = None,
    demand_service: DemandSvcDep = None,
):
    if payment_type not in (
        PaymentType.incoming_payment,
        PaymentType.incoming_order,
        PaymentType.outgoing_payment,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Статусы доступны только для входящих платежей, приходных и исходящих платежей"
            ),
        )

    def _map_states(raw_states: list) -> list[dict]:
        return [
            {
                "id": state.get("id", ""),
                "name": state.get("name", ""),
                "color": state.get("color"),
            }
            for state in raw_states
            if state.get("id")
        ]

    payment_states = []

    if payment_type == PaymentType.incoming_payment:
        payment_states = _map_states(await paymentin_service.get_states())
    elif payment_type == PaymentType.incoming_order:
        payment_states = _map_states(await cashin_service.get_states())
    document_states: list[dict] = []

    if document_type == DocumentType.customerorder:
        document_states = _map_states(await customerorder_service.get_states())
    elif document_type == DocumentType.invoiceout:
        document_states = _map_states(await invoiceout_service.get_states())
    elif document_type == DocumentType.demand:
        document_states = _map_states(await demand_service.get_states())

    return StatesResponse(
        payment_states=payment_states,
        document_states=document_states,
        has_payment_states=bool(payment_states),
        has_document_states=bool(document_states),
    )


@router.post("/update-link-settings")
async def update_link_settings(
    payload: UpdateLinkSettingsPayload,
    service: WebhookSvcDep,
):
    logger.info(
        "Обновление настроек привязки: payment_type=%s, document_type=%s, link_type=%s, priority=%s, mask=%s, pay_success=%s, pay_fail=%s, doc_success=%s, doc_fail=%s, transfer_project=%s, check_org=%s",
        payload.payment_type,
        payload.document_type,
        payload.link_type,
        payload.document_priority,
        payload.payment_purpose_mask,
        payload.payment_status_on_success,
        payload.payment_status_on_failure,
        payload.document_status_on_success,
        payload.document_status_on_failure,
        payload.transfer_project_to_payment,
        payload.check_document_organization,
    )

    result = await service.update_link_settings(
        payment_type=payload.payment_type,
        document_type=payload.document_type,
        link_type=payload.link_type,
        document_priority=payload.document_priority,
        payment_purpose_mask=payload.payment_purpose_mask,
        payment_status_on_success=payload.payment_status_on_success,
        payment_status_on_failure=payload.payment_status_on_failure,
        document_status_on_success=payload.document_status_on_success,
        document_status_on_failure=payload.document_status_on_failure,
        transfer_project_to_payment=payload.transfer_project_to_payment,
        check_document_organization=payload.check_document_organization,
    )

    return result


@router.post("/auto-link-toggle")
async def auto_link_toggle(payload: AutoLinkTogglePayload, service: WebhookSvcDep):
    logger.info(
        "UI toggle: payment_type=%s, enabled=%s, document_type=%s, link_type=%s, priority=%s, mask=%s, pay_success=%s, pay_fail=%s, doc_success=%s, doc_fail=%s, transfer_project=%s, check_org=%s",
        payload.payment_type,
        payload.enabled,
        payload.document_type,
        payload.link_type,
        payload.document_priority,
        payload.payment_purpose_mask,
        payload.payment_status_on_success,
        payload.payment_status_on_failure,
        payload.document_status_on_success,
        payload.document_status_on_failure,
        payload.transfer_project_to_payment,
        payload.check_document_organization,
    )

    result = await service.toggle_webhook(
        payment_type=payload.payment_type,
        enabled=payload.enabled,
        document_type=payload.document_type,
        link_type=payload.link_type,
        document_priority=payload.document_priority,
        payment_purpose_mask=payload.payment_purpose_mask,
        payment_status_on_success=payload.payment_status_on_success,
        payment_status_on_failure=payload.payment_status_on_failure,
        document_status_on_success=payload.document_status_on_success,
        document_status_on_failure=payload.document_status_on_failure,
        transfer_project_to_payment=payload.transfer_project_to_payment,
        check_document_organization=payload.check_document_organization,
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
    cashin_service: CashInSvcDep,
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
        cashin_service=cashin_service,
        customerorder_service=customerorder_service,
        invoiceout_service=invoiceout_service,
        demand_service=demand_service,
    )

    return Response(status_code=204)