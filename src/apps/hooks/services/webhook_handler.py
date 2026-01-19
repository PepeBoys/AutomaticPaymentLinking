"""Обработчик webhook событий для автоматической привязки платежей."""

import logging
import re
from datetime import datetime

from ...cashin.exceptions import CashInNotFoundError
from ...cashin.services.cashin_service import CashInService
from ...cashout.exceptions import CashOutNotFoundError
from ...cashout.services.cashout_service import CashOutService
from ...customerorder.exceptions import CustomerOrderNotFoundError
from ...customerorder.services.customerorder_service import CustomerOrderService
from ...demand.exceptions import DemandNotFoundError
from ...demand.services.demand_service import DemandService
from ...invoicein.exceptions import InvoiceInNotFoundError
from ...invoicein.services.invoicein_service import InvoiceInService
from ...invoiceout.exceptions import InvoiceOutNotFoundError
from ...invoiceout.services.invoiceout_service import InvoiceOutService
from ...paymentin.exceptions import PaymentInNotFoundError
from ...paymentin.services.paymentin_service import PaymentInService
from ...paymentout.exceptions import PaymentOutNotFoundError
from ...paymentout.services.paymentout_service import PaymentOutService
from ...purchaseorder.exceptions import PurchaseOrderNotFoundError
from ...purchaseorder.services.purchaseorder_service import PurchaseOrderService
from ...supply.exceptions import SupplyNotFoundError
from ...supply.services.supply_service import SupplyService
from ..domain.entities import WebhookEntity
from ..schemas import DocumentPriority, DocumentType, LinkType

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Обработчик webhook событий для автоматической привязки платежей."""

    def __init__(
        self,
        paymentin_service: PaymentInService,
        cashin_service: CashInService,
        paymentout_service: PaymentOutService,
        cashout_service: CashOutService,
        customerorder_service: CustomerOrderService,
        invoiceout_service: InvoiceOutService,
        demand_service: DemandService,
        purchaseorder_service: PurchaseOrderService,
        invoicein_service: InvoiceInService,
        supply_service: SupplyService,
    ):
        self.paymentin_service = paymentin_service
        self.cashin_service = cashin_service
        self.paymentout_service = paymentout_service
        self.cashout_service = cashout_service
        self.customerorder_service = customerorder_service
        self.invoiceout_service = invoiceout_service
        self.demand_service = demand_service
        self.purchaseorder_service = purchaseorder_service
        self.invoicein_service = invoicein_service
        self.supply_service = supply_service

    async def _handle_incoming_payment(
        self,
        payment_service,
        event_href: str,
        subscription: WebhookEntity,
        not_found_exception: type[Exception],
        payment_label: str,
    ) -> dict:
        """Обработать событие создания входящего платежа/ордера."""

        try:
            payment = await payment_service.get_by_href(event_href)
            logger.info(
                "Обработка %s: id=%s, sum=%s, agent=%s",
                payment_label,
                payment.id,
                payment.sum,
                payment.agent_id,
            )

            if payment.linked_operations:
                logger.info(
                    "%s %s уже содержит привязки (%d). Пропускаем обработку.",
                    payment_label.capitalize(),
                    payment.id,
                    len(payment.linked_operations),
                )
                return {
                    "success": False,
                    "message": (
                        f"{payment_label.capitalize()} уже привязан к документу, обработка пропущена"
                    ),
                    "payment_id": payment.id,
                }

            linked_documents = []
            if subscription.link_type == LinkType.counterparty:
                document, linked_sum, linked_documents = await self._link_payment_by_counterparty(
                    payment_service=payment_service,
                    payment=payment,
                    document_type=subscription.document_type,
                    organization_id=(
                        payment.organization_id
                        if subscription.check_document_organization
                        else None
                    ),
                    prioritize_oldest=(
                        subscription.document_priority == DocumentPriority.oldest_first
                    ),
                    payment_label=payment_label,
                )
            else:
                document = await self._find_document_for_payment(
                    payment=payment,
                    document_type=subscription.document_type,
                    link_type=subscription.link_type,
                    payment_purpose_mask=subscription.payment_purpose_mask,
                    organization_id=(
                        payment.organization_id
                        if subscription.check_document_organization
                        else None
                    ),
                    prioritize_oldest=(
                        subscription.document_priority == DocumentPriority.oldest_first
                    ),
                )
                linked_sum = payment.sum if document else 0
                if document:
                    linked_documents = [document]

            if not document or linked_sum <= 0:
                logger.warning(
                    "Не найден документ для %s %s (agent=%s, sum=%s, strategy=%s, type=%s)",
                    payment_label,
                    payment.id,
                    payment.agent_id,
                    payment.sum,
                    subscription.link_type,
                    subscription.document_type,
                )
                await self._apply_payment_state(
                    payment_service,
                    payment.id,
                    subscription.payment_status_on_failure,
                )
                return {
                    "success": False,
                    "message": "Не найден подходящий документ для привязки",
                }

            if subscription.link_type != LinkType.counterparty:
                await payment_service.link_to_document(
                    payment_id=payment.id,
                    document_meta_href=document.meta_href,
                    linked_sum=payment.sum,
                )

            await self._apply_project_from_document(
                payment_service=payment_service,
                payment_id=payment.id,
                document=document,
                transfer_project=subscription.transfer_project_to_payment,
                payment_label=payment_label,
            )

            await self._apply_sales_channel_from_document(
                payment_service=payment_service,
                payment_id=payment.id,
                document=document,
                transfer_sales_channel=subscription.transfer_sales_channel_to_payment,
                payment_label=payment_label,
            )

            logger.info(
                "✓ %s %s привязан к %s %s (сумма: %s)",
                payment_label.capitalize(),
                payment.id,
                subscription.document_type.value,
                document.name,
                payment.sum,
            )

            await self._apply_payment_state(
                payment_service, payment.id, subscription.payment_status_on_success
            )
            await self._apply_document_states(
                linked_documents,
                subscription.document_type,
                subscription.document_status_on_success,
            )

            response = {
                "success": True,
                "message": (
                    f"{payment_label.capitalize()} привязан к {subscription.document_type.value} {document.name}"
                ),
                "payment_id": payment.id,
                "document_id": document.id,
                "document_type": subscription.document_type.value,
            }

            if subscription.document_type == DocumentType.customerorder:
                response["order_id"] = document.id

            return response

        except not_found_exception as exc:  # type: ignore[misc]
            logger.warning(
                "%s по ссылке %s не найден: %s",
                payment_label.capitalize(),
                event_href,
                exc,
            )
            return {
                "success": False,
                "message": f"{payment_label.capitalize()} не найден в МойСклад",
            }
        except (
            CustomerOrderNotFoundError,
            InvoiceOutNotFoundError,
            DemandNotFoundError,
            PurchaseOrderNotFoundError,
            InvoiceInNotFoundError,
            SupplyNotFoundError,
        ) as exc:
            logger.warning("Документ для %s %s не найден: %s", payment_label, event_href, exc)
            await self._apply_payment_state(
                payment_service,
                getattr(payment, "id", None),
                subscription.payment_status_on_failure,
            )
            return {"success": False, "message": "Документ для привязки не найден"}
        except Exception as exc:  # pragma: no cover - защитный блок
            logger.exception("Ошибка при обработке %s: %s", payment_label, str(exc))
            raise

    async def handle_paymentin_create(
        self, event_href: str, subscription: WebhookEntity
    ) -> dict:
        return await self._handle_incoming_payment(
            payment_service=self.paymentin_service,
            event_href=event_href,
            subscription=subscription,
            not_found_exception=PaymentInNotFoundError,
            payment_label="платеж",
        )

    async def handle_cashin_create(
        self, event_href: str, subscription: WebhookEntity
    ) -> dict:
        return await self._handle_incoming_payment(
            payment_service=self.cashin_service,
            event_href=event_href,
            subscription=subscription,
            not_found_exception=CashInNotFoundError,
            payment_label="приходный ордер",
        )

    async def handle_paymentout_create(
        self, event_href: str, subscription: WebhookEntity
    ) -> dict:
        return await self._handle_incoming_payment(
            payment_service=self.paymentout_service,
            event_href=event_href,
            subscription=subscription,
            not_found_exception=PaymentOutNotFoundError,
            payment_label="платеж",
        )

    async def handle_cashout_create(
        self, event_href: str, subscription: WebhookEntity
    ) -> dict:
        return await self._handle_incoming_payment(
            payment_service=self.cashout_service,
            event_href=event_href,
            subscription=subscription,
            not_found_exception=CashOutNotFoundError,
            payment_label="расходный ордер",
        )

    async def _find_document_for_payment(
        self,
        payment,
        document_type: DocumentType,
        link_type: LinkType,
        payment_purpose_mask: str | None = None,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ):
        """Найти подходящий документ по типу и стратегии."""

        if document_type == DocumentType.customerorder:
            return await self._find_order_for_payment(
                payment,
                link_type,
                payment_purpose_mask,
                organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.invoiceout:
            return await self._find_invoice_for_payment(
                payment,
                link_type,
                payment_purpose_mask,
                organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.demand:
            return await self._find_demand_for_payment(
                payment,
                link_type,
                payment_purpose_mask,
                organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.purchaseorder:
            return await self._find_purchaseorder_for_payment(
                payment,
                link_type,
                payment_purpose_mask,
                organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.invoicein:
            return await self._find_invoicein_for_payment(
                payment,
                link_type,
                payment_purpose_mask,
                organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.supply:
            return await self._find_supply_for_payment(
                payment,
                link_type,
                payment_purpose_mask,
                organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        return None

    async def _link_payment_by_counterparty(
        self,
        payment_service,
        payment,
        document_type: DocumentType,
        organization_id: str | None,
        prioritize_oldest: bool,
        payment_label: str,
    ):
        """Привязать платеж по контрагенту к нескольким документам по очереди."""

        documents = await self._get_documents_by_counterparty(
            payment=payment,
            document_type=document_type,
            organization_id=organization_id,
            prioritize_oldest=prioritize_oldest,
        )

        if not documents:
            return None, 0, []

        remaining_sum = payment.sum
        last_linked_document = None
        linked_documents: list = []

        for document in documents:
            unpaid_amount = document.get_unpaid_amount()
            if unpaid_amount <= 0:
                continue

            linked_sum = min(unpaid_amount, remaining_sum)

            if linked_sum <= 0:
                break

            await payment_service.link_to_document(
                payment_id=payment.id,
                document_meta_href=document.meta_href,
                linked_sum=linked_sum,
            )

            logger.info(
                "Часть %s %s привязана к %s %s: linked_sum=%s, unpaid_before=%s, remaining_payment=%s",
                payment_label,
                payment.id,
                document_type.value,
                document.name,
                linked_sum,
                unpaid_amount,
                remaining_sum - linked_sum,
            )

            remaining_sum -= linked_sum
            last_linked_document = document
            linked_documents.append(document)

            if remaining_sum <= 0:
                break

        if remaining_sum > 0 and documents:
            fallback_document = last_linked_document or documents[-1]
            await payment_service.link_to_document(
                payment_id=payment.id,
                document_meta_href=fallback_document.meta_href,
                linked_sum=remaining_sum,
            )
            logger.info(
                "Остаток %s %s привязан к %s %s: linked_sum=%s",
                payment_label,
                payment.id,
                document_type.value,
                fallback_document.name,
                remaining_sum,
            )
            if fallback_document not in linked_documents:
                linked_documents.append(fallback_document)
            last_linked_document = fallback_document
            remaining_sum = 0

        total_linked = payment.sum - remaining_sum
        return last_linked_document, total_linked, linked_documents

    async def _apply_payment_state(
        self, payment_service, payment_id: str | None, state_id: str | None
    ) -> None:
        """Применить статус к платежу, если задан."""

        if payment_id and state_id:
            await payment_service.update_state(payment_id, state_id)

    async def _apply_project_from_document(
        self,
        payment_service,
        payment_id: str,
        document,
        transfer_project: bool,
        payment_label: str,
    ) -> None:
        """Перенести проект из документа в платеж при необходимости."""

        if not transfer_project:
            return

        project_href = getattr(document, "project_meta_href", None) if document else None

        if not project_href:
            logger.info(
                "Проект не перенесен для %s %s: у документа нет проекта",
                payment_label,
                payment_id,
            )
            return

        try:
            await payment_service.update_project(payment_id, project_href)
            logger.info(
                "✓ Проект перенесен в %s %s из документа %s",
                payment_label,
                payment_id,
                document.name if document else "",
            )
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            logger.warning(
                "Не удалось перенести проект в %s %s: %s",
                payment_label,
                payment_id,
                exc,
            )

    async def _apply_sales_channel_from_document(
        self,
        payment_service,
        payment_id: str,
        document,
        transfer_sales_channel: bool,
        payment_label: str,
    ) -> None:
        """Перенести канал продаж из документа в платеж при необходимости."""

        if not transfer_sales_channel:
            return

        sales_channel_href = (
            getattr(document, "sales_channel_meta_href", None) if document else None
        )

        if not sales_channel_href:
            logger.info(
                "Канал продаж не перенесен для %s %s: у документа нет канала продаж",
                payment_label,
                payment_id,
            )
            return

        try:
            await payment_service.update_sales_channel(payment_id, sales_channel_href)
            logger.info(
                "✓ Канал продаж перенесен в %s %s из документа %s",
                payment_label,
                payment_id,
                document.name if document else "",
            )
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            logger.warning(
                "Не удалось перенести канал продаж в %s %s: %s",
                payment_label,
                payment_id,
                exc,
            )

    async def _apply_document_states(
        self,
        documents: list,
        document_type: DocumentType,
        state_id: str | None,
    ) -> None:
        """Применить статус ко всем найденным документам."""

        if not state_id or not documents:
            return

        for document in documents:
            if document_type == DocumentType.customerorder:
                await self.customerorder_service.update_state(document.id, state_id)
            elif document_type == DocumentType.invoiceout:
                await self.invoiceout_service.update_state(document.id, state_id)
            elif document_type == DocumentType.demand:
                await self.demand_service.update_state(document.id, state_id)
            elif document_type == DocumentType.purchaseorder:
                await self.purchaseorder_service.update_state(document.id, state_id)
            elif document_type == DocumentType.invoicein:
                await self.invoicein_service.update_state(document.id, state_id)
            elif document_type == DocumentType.supply:
                await self.supply_service.update_state(document.id, state_id)

    async def _get_documents_by_counterparty(
        self,
        payment,
        document_type: DocumentType,
        organization_id: str | None,
        prioritize_oldest: bool,
    ):
        """Получить список документов для привязки по контрагенту."""

        if document_type == DocumentType.customerorder:
            return await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.invoiceout:
            return await self.invoiceout_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.demand:
            return await self.demand_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.purchaseorder:
            return await self.purchaseorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.invoicein:
            return await self.invoicein_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.supply:
            return await self.supply_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        return []

    async def _find_order_for_payment(
        self,
        payment,
        link_type: LinkType,
        payment_purpose_mask: str | None = None,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ):
        """Найти подходящий заказ в зависимости от стратегии."""

        if link_type == LinkType.sum_and_counterparty:
            orders = await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
                organization_id=organization_id,
            )
            return orders[0] if orders else None

        elif link_type == LinkType.counterparty:
            orders = await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
            )
            return orders[0] if orders else None

        elif link_type == LinkType.payment_purpose_mask:
            return await self._find_document_by_purpose_mask(
                payment=payment,
                document_type=DocumentType.customerorder,
                payment_purpose_mask=payment_purpose_mask,
                organization_id=organization_id,
            )

        return None

    async def _find_invoice_for_payment(
        self,
        payment,
        link_type: LinkType,
        payment_purpose_mask: str | None = None,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ):
        """Найти подходящий счет покупателю для платежа."""

        if link_type == LinkType.sum_and_counterparty:
            invoices = await self.invoiceout_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
                organization_id=organization_id,
            )
            return invoices[0] if invoices else None

        if link_type == LinkType.counterparty:
            invoices = await self.invoiceout_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
            )
            return invoices[0] if invoices else None

        if link_type == LinkType.payment_purpose_mask:
            return await self._find_document_by_purpose_mask(
                payment=payment,
                document_type=DocumentType.invoiceout,
                payment_purpose_mask=payment_purpose_mask,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        return None

    async def _find_demand_for_payment(
        self,
        payment,
        link_type: LinkType,
        payment_purpose_mask: str | None = None,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ):
        """Найти подходящую отгрузку для платежа."""

        if link_type == LinkType.sum_and_counterparty:
            demands = await self.demand_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
                organization_id=organization_id,
            )
            return demands[0] if demands else None

        if link_type == LinkType.counterparty:
            demands = await self.demand_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
            )
            return demands[0] if demands else None

        if link_type == LinkType.payment_purpose_mask:
            return await self._find_document_by_purpose_mask(
                payment=payment,
                document_type=DocumentType.demand,
                payment_purpose_mask=payment_purpose_mask,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        return None

    async def _find_purchaseorder_for_payment(
        self,
        payment,
        link_type: LinkType,
        payment_purpose_mask: str | None = None,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ):
        """Найти подходящий заказ поставщику для платежа."""

        if link_type == LinkType.sum_and_counterparty:
            orders = await self.purchaseorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
                organization_id=organization_id,
            )
            return orders[0] if orders else None

        if link_type == LinkType.counterparty:
            orders = await self.purchaseorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
            )
            return orders[0] if orders else None

        if link_type == LinkType.payment_purpose_mask:
            return await self._find_document_by_purpose_mask(
                payment=payment,
                document_type=DocumentType.purchaseorder,
                payment_purpose_mask=payment_purpose_mask,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        return None

    async def _find_invoicein_for_payment(
        self,
        payment,
        link_type: LinkType,
        payment_purpose_mask: str | None = None,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ):
        """Найти подходящий счет поставщика для платежа."""

        if link_type == LinkType.sum_and_counterparty:
            invoices = await self.invoicein_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
                organization_id=organization_id,
            )
            return invoices[0] if invoices else None

        if link_type == LinkType.counterparty:
            invoices = await self.invoicein_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
            )
            return invoices[0] if invoices else None

        if link_type == LinkType.payment_purpose_mask:
            return await self._find_document_by_purpose_mask(
                payment=payment,
                document_type=DocumentType.invoicein,
                payment_purpose_mask=payment_purpose_mask,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        return None

    async def _find_supply_for_payment(
        self,
        payment,
        link_type: LinkType,
        payment_purpose_mask: str | None = None,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ):
        """Найти подходящую приемку для платежа."""

        if link_type == LinkType.sum_and_counterparty:
            supplies = await self.supply_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
                organization_id=organization_id,
            )
            return supplies[0] if supplies else None

        if link_type == LinkType.counterparty:
            supplies = await self.supply_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                organization_id=organization_id,
            )
            return supplies[0] if supplies else None

        if link_type == LinkType.payment_purpose_mask:
            return await self._find_document_by_purpose_mask(
                payment=payment,
                document_type=DocumentType.supply,
                payment_purpose_mask=payment_purpose_mask,
                organization_id=organization_id,
                prioritize_oldest=prioritize_oldest,
            )

        return None

    async def _find_document_by_purpose_mask(
        self,
        payment,
        document_type: DocumentType,
        payment_purpose_mask: str | None,
        organization_id: str | None,
        prioritize_oldest: bool = True,
    ):
        """Найти документ по данным из назначения платежа."""

        name, moment = self._extract_details_from_purpose(
            payment_purpose=payment.payment_purpose,
            payment_purpose_mask=payment_purpose_mask,
        )

        if not name:
            return None

        try:
            if document_type == DocumentType.customerorder:
                return await self.customerorder_service.find_by_name_and_agent(
                    name=name,
                    agent_id=payment.agent_id,
                    organization_id=organization_id,
                    moment=moment,
                    prioritize_oldest=prioritize_oldest,
                )

            if document_type == DocumentType.invoiceout:
                return await self.invoiceout_service.find_by_name_and_agent(
                    name=name,
                    agent_id=payment.agent_id,
                    organization_id=organization_id,
                    moment=moment,
                    prioritize_oldest=prioritize_oldest,
                )

            if document_type == DocumentType.demand:
                return await self.demand_service.find_by_name_and_agent(
                    name=name,
                    agent_id=payment.agent_id,
                    organization_id=organization_id,
                    moment=moment,
                    prioritize_oldest=prioritize_oldest,
                )

            if document_type == DocumentType.purchaseorder:
                return await self.purchaseorder_service.find_by_name_and_agent(
                    name=name,
                    agent_id=payment.agent_id,
                    organization_id=organization_id,
                    moment=moment,
                    prioritize_oldest=prioritize_oldest,
                )

            if document_type == DocumentType.invoicein:
                return await self.invoicein_service.find_by_name_and_agent(
                    name=name,
                    agent_id=payment.agent_id,
                    organization_id=organization_id,
                    moment=moment,
                    prioritize_oldest=prioritize_oldest,
                )

            if document_type == DocumentType.supply:
                return await self.supply_service.find_by_name_and_agent(
                    name=name,
                    agent_id=payment.agent_id,
                    organization_id=organization_id,
                    moment=moment,
                    prioritize_oldest=prioritize_oldest,
                )
        except (
            CustomerOrderNotFoundError,
            InvoiceOutNotFoundError,
            DemandNotFoundError,
            PurchaseOrderNotFoundError,
            InvoiceInNotFoundError,
            SupplyNotFoundError,
        ):
            return None

        return None

    def _extract_details_from_purpose(
        self, payment_purpose: str | None, payment_purpose_mask: str | None
    ):
        if not payment_purpose:
            return None, None

        if payment_purpose_mask:
            regex = self._build_mask_regex(payment_purpose_mask)
            match = regex.search(payment_purpose)
            if match:
                name = match.groupdict().get("name")
                moment_str = match.groupdict().get("moment")
                moment = self._parse_moment(moment_str) if moment_str else None
                return name.strip() if name else None, moment

        generic_match = re.search(
            r"№\s*(?P<name>.+?)(?:\s+от\s+(?P<moment>\d{1,2}[./-]\d{1,2}[./-]\d{2,4}))?(?:\b|$)",
            payment_purpose,
            re.IGNORECASE,
        )
        if generic_match:
            name = generic_match.group("name")
            moment_str = generic_match.group("moment")
            return name.strip(), self._parse_moment(moment_str)

        patterns = [
            r"(?:заказ|order|№)\s*(\d+)",
            r"\b(\d{5,})\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, payment_purpose, re.IGNORECASE)
            if match:
                return match.group(1), None

        logger.warning(
            "Не удалось извлечь данные из назначения платежа: '%s'", payment_purpose
        )
        return None, None

    @staticmethod
    def _build_mask_regex(payment_purpose_mask: str) -> re.Pattern:
        placeholder_pattern = (
            r"№\s*(?P<name>.+?)(?:\s+от\s+(?P<moment>\d{1,2}[./-]\d{1,2}[./-]\d{2,4}))?(?:\b|$)"
        )

        return re.compile(placeholder_pattern, re.IGNORECASE)

    @staticmethod
    def _parse_moment(moment_str: str | None) -> datetime | None:
        if not moment_str:
            return None

        for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(moment_str, fmt)
            except ValueError:
                pass

        logger.warning("Не удалось распарсить дату '%s' из назначения платежа", moment_str)
        return None
