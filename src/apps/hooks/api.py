import logging
from asyncio import Lock

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..cashin.dependencies import CashInSvcDep
from ..cashout.dependencies import CashOutSvcDep
from ..customerorder.dependencies import CustomerOrderSvcDep
from ..demand.dependencies import DemandSvcDep
from ..invoicein.dependencies import InvoiceInSvcDep
from ..invoiceout.dependencies import InvoiceOutSvcDep
from ..paymentin.dependencies import PaymentInSvcDep
from ..paymentin.services.paymentin_service import PaymentInService
from ..paymentout.dependencies import PaymentOutSvcDep
from ..paymentout.services.paymentout_service import PaymentOutService
from ..purchaseorder.dependencies import PurchaseOrderSvcDep
from ..purchaseorder.services.purchaseorder_service import PurchaseOrderService
from ..supply.dependencies import SupplySvcDep
from ..supply.services.supply_service import SupplyService
from src.apps.cashin.services.cashin_service import CashInService
from src.apps.cashout.services.cashout_service import CashOutService
from src.apps.customerorder.services.customerorder_service import CustomerOrderService
from src.apps.demand.services.demand_service import DemandService
from src.apps.invoicein.services.invoicein_service import InvoiceInService
from src.apps.invoiceout.services.invoiceout_service import InvoiceOutService
from src.apps.ms_auth.services.auth_service import build_ms_auth_service
from src.apps.vendor_api.repository import VendorAccountRepository
from src.core.config import settings
from src.core.database import async_session_maker, get_session
from .dependencies import (
    RequestIdQuery,
    WebhookSvcDep,
)
from .schemas import (
    AutoLinkTogglePayload,
    DocumentType,
    MySkladWebhookPayload,
    PaymentType,
    StatesResponse,
    UpdateLinkSettingsPayload,
    WebhookStatusResponse,
)
from .services.webhook_service import WebhookService
from .uow.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

router = APIRouter()
_ACCOUNT_LOCKS: dict[str, Lock] = {}


def _get_account_lock(account_id: str) -> Lock:
    lock = _ACCOUNT_LOCKS.get(account_id)
    if lock is None:
        lock = Lock()
        _ACCOUNT_LOCKS[account_id] = lock
    return lock


async def _process_moysklad_webhook(
    *,
    account_id: str,
    payload: MySkladWebhookPayload,
    request_id: str,
) -> None:
    lock = _get_account_lock(account_id)
    async with lock, async_session_maker() as session:
        repo = VendorAccountRepository(session)
        account = await repo.get_by_account_id(account_id)

        if not account or not account.is_active or not account.access_token:
            logger.warning(
                "Webhook skipped: account inactive or missing token: requestId=%s, accountId=%s",
                request_id,
                account_id,
            )
            return

        auth_service = build_ms_auth_service()
        auth_service.set_access_token(
            account.access_token,
            base_url=account.base_url or settings.ms_base_url,
            account_id=account.account_id,
        )

        service = WebhookService(uow=UnitOfWork(session), auth_service=auth_service)
        await service.process_incoming_webhook(
            request_id=request_id,
            payload=payload,
            paymentin_service=PaymentInService(auth_service),
            cashin_service=CashInService(auth_service),
            paymentout_service=PaymentOutService(auth_service),
            cashout_service=CashOutService(auth_service),
            customerorder_service=CustomerOrderService(auth_service),
            invoiceout_service=InvoiceOutService(auth_service),
            demand_service=DemandService(auth_service),
            purchaseorder_service=PurchaseOrderService(auth_service),
            invoicein_service=InvoiceInService(auth_service),
            supply_service=SupplyService(auth_service),
        )


async def _process_moysklad_webhook(
    *,
    account_id: str,
    payload: MySkladWebhookPayload,
    request_id: str,
) -> None:
    async with async_session_maker() as session:
        repo = VendorAccountRepository(session)
        account = await repo.get_by_account_id(account_id)

        if not account or not account.is_active or not account.access_token:
            logger.warning(
                "Webhook skipped: account inactive or missing token: requestId=%s, accountId=%s",
                request_id,
                account_id,
            )
            return

        auth_service = build_ms_auth_service()
        auth_service.set_access_token(
            account.access_token,
            base_url=account.base_url or settings.ms_base_url,
            account_id=account.account_id,
        )

        service = WebhookService(uow=UnitOfWork(session), auth_service=auth_service)
        await service.process_incoming_webhook(
            request_id=request_id,
            payload=payload,
            paymentin_service=PaymentInService(auth_service),
            cashin_service=CashInService(auth_service),
            paymentout_service=PaymentOutService(auth_service),
            cashout_service=CashOutService(auth_service),
            customerorder_service=CustomerOrderService(auth_service),
            invoiceout_service=InvoiceOutService(auth_service),
            demand_service=DemandService(auth_service),
            purchaseorder_service=PurchaseOrderService(auth_service),
            invoicein_service=InvoiceInService(auth_service),
            supply_service=SupplyService(auth_service),
        )


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
        payment_purpose_mask=payload.payment_purpose_mask,
        payment_status_on_success=payload.payment_status_on_success,
        payment_status_on_failure=payload.payment_status_on_failure,
        document_status_on_success=payload.document_status_on_success,
        transfer_project_to_payment=payload.transfer_project_to_payment,
        transfer_sales_channel_to_payment=payload.transfer_sales_channel_to_payment,
        check_document_organization=payload.check_document_organization,
    )

    return result


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
        payment_purpose_mask=payload.payment_purpose_mask,
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
    payload: MySkladWebhookPayload,
    request_id: RequestIdQuery = None,
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_session),
) -> Response:
    events = payload.events or []
    events_count = len(events)
    account_ids = {
        event.accountId for event in events if event and event.accountId is not None
    }
    has_missing_fields = any(
        event.accountId is None or event.meta is None or event.action is None
        for event in events
    )

    if (
        not request_id
        or events_count == 0
        or len(account_ids) != 1
        or has_missing_fields
    ):
        account_id = next(iter(account_ids), None)
        logger.warning(
            "Webhook invalid_payload: requestId=%s, accountId=%s, events=%d",
            request_id,
            account_id,
            events_count,
        )
        return Response(status_code=204)

    account_id = next(iter(account_ids))

    service = WebhookService(
        uow=UnitOfWork(session),
        auth_service=build_ms_auth_service(),
    )
    result = await service.register_webhook_request(
        request_id=request_id,
        account_id=account_id,
        events_count=events_count,
    )

    logger.info(
        "Webhook %s: requestId=%s, accountId=%s, events=%d",
        result,
        request_id,
        account_id,
        events_count,
    )

    if result == "duplicate":
        return Response(status_code=204)

    if background_tasks is None:
        background_tasks = BackgroundTasks()

    background_tasks.add_task(
        _process_moysklad_webhook,
        account_id=account_id,
        payload=payload,
        request_id=request_id,
    )

    return Response(status_code=204)
