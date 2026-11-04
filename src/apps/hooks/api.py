import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from ..cashin.dependencies import CashInSvcDep
from ..cashout.dependencies import CashOutSvcDep
from ..customerorder.dependencies import CustomerOrderSvcDep
from ..demand.dependencies import DemandSvcDep
from ..expense_sync.dependencies import ExpenseSyncHandlerDep
from ..document_items.dependencies import DocumentItemsHandlerDep
from ..income_sync.dependencies import IncomeSyncHandlerDep
from ..invoicein.dependencies import InvoiceInSvcDep
from ..invoiceout.dependencies import InvoiceOutSvcDep
from ..paymentin.dependencies import PaymentInSvcDep
from ..paymentout.dependencies import PaymentOutSvcDep
from ..purchaseorder.dependencies import PurchaseOrderSvcDep
from ..supply.dependencies import SupplySvcDep
from .dependencies import (
    RequestIdQuery,
    WebhookSvcDep,
    set_request_account_from_webhook,
)
from .purpose_templates import test_templates
from .schemas import (
    AutoLinkTogglePayload,
    DocumentType,
    MySkladWebhookPayload,
    PaymentType,
    PurposeTemplateTestResult,
    StatesResponse,
    TestPurposeTemplatePayload,
    TestPurposeTemplateResponse,
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
    paymentout_service: PaymentOutSvcDep = None,
    cashout_service: CashOutSvcDep = None,
    customerorder_service: CustomerOrderSvcDep = None,
    invoiceout_service: InvoiceOutSvcDep = None,
    demand_service: DemandSvcDep = None,
    purchaseorder_service: PurchaseOrderSvcDep = None,
    invoicein_service: InvoiceInSvcDep = None,
    supply_service: SupplySvcDep = None,
):
    if payment_type not in (
        PaymentType.incoming_payment,
        PaymentType.incoming_order,
        PaymentType.outgoing_payment,
        PaymentType.outgoing_order,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Статусы доступны только для входящих/исходящих платежей и приходных/расходных ордеров"
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
    elif payment_type == PaymentType.outgoing_payment:
        payment_states = _map_states(await paymentout_service.get_states())
    elif payment_type == PaymentType.outgoing_order:
        payment_states = _map_states(await cashout_service.get_states())
    document_states: list[dict] = []

    if document_type == DocumentType.customerorder:
        document_states = _map_states(await customerorder_service.get_states())
    elif document_type == DocumentType.invoiceout:
        document_states = _map_states(await invoiceout_service.get_states())
    elif document_type == DocumentType.demand:
        document_states = _map_states(await demand_service.get_states())
    elif document_type == DocumentType.purchaseorder:
        document_states = _map_states(await purchaseorder_service.get_states())
    elif document_type == DocumentType.invoicein:
        document_states = _map_states(await invoicein_service.get_states())
    elif document_type == DocumentType.supply:
        document_states = _map_states(await supply_service.get_states())

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
        "Обновление настроек привязки: payment_type=%s, document_type=%s, link_type=%s, priority=%s, mask=%s, pay_success=%s, pay_failure=%s, doc_success=%s, transfer_project=%s, transfer_channel=%s, check_org=%s",
        payload.payment_type,
        payload.document_type,
        payload.link_type,
        payload.document_priority,
        payload.payment_purpose_mask,
        payload.payment_status_on_success,
        payload.payment_status_on_failure,
        payload.document_status_on_success,
        payload.transfer_project_to_payment,
        payload.transfer_sales_channel_to_payment,
        payload.check_document_organization,
    )

    result = await service.update_link_settings(
        payment_type=payload.payment_type,
        document_type=payload.document_type,
        link_type=payload.link_type,
        document_priority=payload.document_priority,
        payment_purpose_masks=payload.payment_purpose_mask,
        payment_status_on_success=payload.payment_status_on_success,
        payment_status_on_failure=payload.payment_status_on_failure,
        document_status_on_success=payload.document_status_on_success,
        transfer_project_to_payment=payload.transfer_project_to_payment,
        transfer_sales_channel_to_payment=payload.transfer_sales_channel_to_payment,
        check_document_organization=payload.check_document_organization,
    )

    return result


@router.post("/test-purpose-template", response_model=TestPurposeTemplateResponse)
async def test_purpose_template(payload: TestPurposeTemplatePayload):
    """Прогнать пример назначения платежа по шаблонам без сохранения настроек."""
    results = test_templates(payload.payment_purpose, payload.templates)

    matched_index = next(
        (index for index, result in enumerate(results) if result["matched"]),
        None,
    )

    return TestPurposeTemplateResponse(
        results=[PurposeTemplateTestResult(**result) for result in results],
        matched_index=matched_index,
    )


@router.post("/auto-link-toggle")
async def auto_link_toggle(payload: AutoLinkTogglePayload, service: WebhookSvcDep):
    logger.info(
        "UI toggle: payment_type=%s, enabled=%s, document_type=%s, link_type=%s, priority=%s, mask=%s, pay_success=%s, pay_failure=%s, doc_success=%s, transfer_project=%s, transfer_channel=%s, check_org=%s",
        payload.payment_type,
        payload.enabled,
        payload.document_type,
        payload.link_type,
        payload.document_priority,
        payload.payment_purpose_mask,
        payload.payment_status_on_success,
        payload.payment_status_on_failure,
        payload.document_status_on_success,
        payload.transfer_project_to_payment,
        payload.transfer_sales_channel_to_payment,
        payload.check_document_organization,
    )

    result = await service.toggle_webhook(
        payment_type=payload.payment_type,
        enabled=payload.enabled,
        document_type=payload.document_type,
        link_type=payload.link_type,
        document_priority=payload.document_priority,
        payment_purpose_masks=payload.payment_purpose_mask,
        payment_status_on_success=payload.payment_status_on_success,
        payment_status_on_failure=payload.payment_status_on_failure,
        document_status_on_success=payload.document_status_on_success,
        transfer_project_to_payment=payload.transfer_project_to_payment,
        transfer_sales_channel_to_payment=payload.transfer_sales_channel_to_payment,
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
    # Должна выполниться первой: кладёт accountId из payload в request.state
    # до того, как сервисы ниже разрешат get_ms_auth_service.
    _: Annotated[None, Depends(set_request_account_from_webhook)],
    payload: MySkladWebhookPayload,
    service: WebhookSvcDep,
    paymentin_service: PaymentInSvcDep,
    cashin_service: CashInSvcDep,
    paymentout_service: PaymentOutSvcDep,
    cashout_service: CashOutSvcDep,
    customerorder_service: CustomerOrderSvcDep,
    invoiceout_service: InvoiceOutSvcDep,
    demand_service: DemandSvcDep,
    purchaseorder_service: PurchaseOrderSvcDep,
    invoicein_service: InvoiceInSvcDep,
    supply_service: SupplySvcDep,
    expense_sync_handler: ExpenseSyncHandlerDep,
    income_sync_handler: IncomeSyncHandlerDep,
    document_items_handler: DocumentItemsHandlerDep,
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
        paymentout_service=paymentout_service,
        cashout_service=cashout_service,
        customerorder_service=customerorder_service,
        invoiceout_service=invoiceout_service,
        demand_service=demand_service,
        purchaseorder_service=purchaseorder_service,
        invoicein_service=invoicein_service,
        supply_service=supply_service,
        expense_sync_handler=expense_sync_handler,
        income_sync_handler=income_sync_handler,
        document_items_handler=document_items_handler,
    )

    return Response(status_code=204)