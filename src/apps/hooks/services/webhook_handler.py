"""Обработчик webhook событий для автоматической привязки платежей."""

import logging
import re
from datetime import datetime

from ...customerorder.exceptions import CustomerOrderNotFoundError
from ...customerorder.services.customerorder_service import CustomerOrderService
from ...demand.exceptions import DemandNotFoundError
from ...demand.services.demand_service import DemandService
from ...invoiceout.exceptions import InvoiceOutNotFoundError
from ...invoiceout.services.invoiceout_service import InvoiceOutService
from ...paymentin.exceptions import PaymentInNotFoundError
from ...paymentin.services.paymentin_service import PaymentInService
from ..domain.entities import WebhookEntity
from ..schemas import DocumentPriority, DocumentType, LinkType

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Обработчик webhook событий для автоматической привязки платежей."""

    def __init__(
        self,
        paymentin_service: PaymentInService,
        customerorder_service: CustomerOrderService,
        invoiceout_service: InvoiceOutService,
        demand_service: DemandService,
    ):
        self.paymentin_service = paymentin_service
        self.customerorder_service = customerorder_service
        self.invoiceout_service = invoiceout_service
        self.demand_service = demand_service

    async def handle_paymentin_create(
        self, event_href: str, subscription: WebhookEntity
    ) -> dict:
        """Обработать событие создания входящего платежа."""

        try:
            payment = await self.paymentin_service.get_by_href(event_href)
            logger.info(
                "Обработка платежа: id=%s, sum=%s, agent=%s",
                payment.id,
                payment.sum,
                payment.agent_id,
            )

            linked_documents = []
            if subscription.link_type == LinkType.counterparty:
                document, linked_sum, linked_documents = await self._link_payment_by_counterparty(
                    payment=payment,
                    document_type=subscription.document_type,
                    prioritize_oldest=(
                        subscription.document_priority == DocumentPriority.oldest_first
                    ),
                )
            else:
                document = await self._find_document_for_payment(
                    payment=payment,
                    document_type=subscription.document_type,
                    link_type=subscription.link_type,
                    payment_purpose_mask=subscription.payment_purpose_mask,
                    prioritize_oldest=(
                        subscription.document_priority == DocumentPriority.oldest_first
                    ),
                )
                linked_sum = payment.sum if document else 0
                if document:
                    linked_documents = [document]

            if not document or linked_sum <= 0:
                logger.warning(
                    "Не найден документ для платежа %s (agent=%s, sum=%s, strategy=%s, type=%s)",
                    payment.id,
                    payment.agent_id,
                    payment.sum,
                    subscription.link_type,
                    subscription.document_type,
                )
                await self._apply_payment_state(
                    payment.id, subscription.payment_status_on_failure
                )
                return {
                    "success": False,
                    "message": "Не найден подходящий документ для привязки",
                }

            if subscription.link_type != LinkType.counterparty:
                await self.paymentin_service.link_to_document(
                    payment_id=payment.id,
                    document_meta_href=document.meta_href,
                    linked_sum=payment.sum,
                )

            await self._apply_project_from_document(
                payment_id=payment.id,
                document=document,
                transfer_project=subscription.transfer_project_to_payment,
            )

            logger.info(
                "✓ Платеж %s привязан к %s %s (сумма: %s)",
                payment.id,
                subscription.document_type.value,
                document.name,
                payment.sum,
            )

            await self._apply_payment_state(
                payment.id, subscription.payment_status_on_success
            )
            await self._apply_document_states(
                linked_documents,
                subscription.document_type,
                subscription.document_status_on_success,
            )

            response = {
                "success": True,
                "message": (
                    f"Платеж привязан к {subscription.document_type.value} {document.name}"
                ),
                "payment_id": payment.id,
                "document_id": document.id,
                "document_type": subscription.document_type.value,
            }

            if subscription.document_type == DocumentType.customerorder:
                response["order_id"] = document.id

            return response

        except PaymentInNotFoundError as exc:
            logger.warning("Платеж по ссылке %s не найден: %s", event_href, exc)
            return {"success": False, "message": "Платеж не найден в МойСклад"}
        except (
            CustomerOrderNotFoundError,
            InvoiceOutNotFoundError,
            DemandNotFoundError,
        ) as exc:
            logger.warning("Документ для платежа %s не найден: %s", event_href, exc)
            await self._apply_payment_state(
                payment.id if 'payment' in locals() else None,
                subscription.payment_status_on_failure,
            )
            return {"success": False, "message": "Документ для привязки не найден"}
        except Exception as exc:  # pragma: no cover - защитный блок
            logger.exception("Ошибка при обработке платежа: %s", str(exc))
            raise

    async def _find_document_for_payment(
        self,
        payment,
        document_type: DocumentType,
        link_type: LinkType,
        payment_purpose_mask: str | None = None,
        prioritize_oldest: bool = True,
    ):
        """Найти подходящий документ по типу и стратегии."""

        if document_type == DocumentType.customerorder:
            return await self._find_order_for_payment(
                payment,
                link_type,
                payment_purpose_mask,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.invoiceout:
            return await self._find_invoice_for_payment(
                payment,
                link_type,
                payment_purpose_mask,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.demand:
            return await self._find_demand_for_payment(
                payment,
                link_type,
                payment_purpose_mask,
                prioritize_oldest=prioritize_oldest,
            )

        return None

    async def _link_payment_by_counterparty(
        self,
        payment,
        document_type: DocumentType,
        prioritize_oldest: bool,
    ):
        """Привязать платеж по контрагенту к нескольким документам по очереди."""

        documents = await self._get_documents_by_counterparty(
            payment=payment,
            document_type=document_type,
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

            await self.paymentin_service.link_to_document(
                payment_id=payment.id,
                document_meta_href=document.meta_href,
                linked_sum=linked_sum,
            )

            logger.info(
                "Часть платежа %s привязана к %s %s: linked_sum=%s, unpaid_before=%s, remaining_payment=%s",
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

        total_linked = payment.sum - remaining_sum
        return last_linked_document, total_linked, linked_documents

    async def _apply_payment_state(self, payment_id: str | None, state_id: str | None) -> None:
        """Применить статус к платежу, если задан."""

        if payment_id and state_id:
            await self.paymentin_service.update_state(payment_id, state_id)

    async def _apply_project_from_document(
        self, payment_id: str, document, transfer_project: bool
    ) -> None:
        """Перенести проект из документа в платеж при необходимости."""

        if not transfer_project:
            return

        project_href = getattr(document, "project_meta_href", None) if document else None

        if not project_href:
            logger.info(
                "Проект не перенесен для платежа %s: у документа нет проекта",
                payment_id,
            )
            return

        try:
            await self.paymentin_service.update_project(payment_id, project_href)
            logger.info(
                "✓ Проект перенесен в платеж %s из документа %s",
                payment_id,
                document.name if document else "",
            )
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            logger.warning(
                "Не удалось перенести проект в платеж %s: %s", payment_id, exc
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

    async def _get_documents_by_counterparty(
        self, payment, document_type: DocumentType, prioritize_oldest: bool
    ):
        """Получить список документов для привязки по контрагенту."""

        if document_type == DocumentType.customerorder:
            return await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.invoiceout:
            return await self.invoiceout_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                prioritize_oldest=prioritize_oldest,
            )

        if document_type == DocumentType.demand:
            return await self.demand_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
                prioritize_oldest=prioritize_oldest,
            )

        return []

    async def _find_order_for_payment(
        self,
        payment,
        link_type: LinkType,
        payment_purpose_mask: str | None = None,
        prioritize_oldest: bool = True,
    ):
        """Найти подходящий заказ в зависимости от стратегии."""

        if link_type == LinkType.sum_and_counterparty:
            orders = await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
            )
            return orders[0] if orders else None

        elif link_type == LinkType.counterparty:
            orders = await self.customerorder_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
            )
            return orders[0] if orders else None

        elif link_type == LinkType.payment_purpose_mask:
            return await self._find_document_by_purpose_mask(
                payment=payment,
                document_type=DocumentType.customerorder,
                payment_purpose_mask=payment_purpose_mask,
            )

        return None

    async def _find_invoice_for_payment(
        self,
        payment,
        link_type: LinkType,
        payment_purpose_mask: str | None = None,
        prioritize_oldest: bool = True,
    ):
        """Найти подходящий счет покупателю для платежа."""

        if link_type == LinkType.sum_and_counterparty:
            invoices = await self.invoiceout_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
            )
            return invoices[0] if invoices else None

        if link_type == LinkType.counterparty:
            invoices = await self.invoiceout_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
            )
            return invoices[0] if invoices else None

        if link_type == LinkType.payment_purpose_mask:
            return await self._find_document_by_purpose_mask(
                payment=payment,
                document_type=DocumentType.invoiceout,
                payment_purpose_mask=payment_purpose_mask,
                prioritize_oldest=prioritize_oldest,
            )

        return None

    async def _find_demand_for_payment(
        self,
        payment,
        link_type: LinkType,
        payment_purpose_mask: str | None = None,
        prioritize_oldest: bool = True,
    ):
        """Найти подходящую отгрузку для платежа."""

        if link_type == LinkType.sum_and_counterparty:
            demands = await self.demand_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=True,
            )
            return demands[0] if demands else None

        if link_type == LinkType.counterparty:
            demands = await self.demand_service.find_for_payment(
                agent_id=payment.agent_id,
                payment_sum=payment.sum,
                search_by_sum=False,
            )
            return demands[0] if demands else None

        if link_type == LinkType.payment_purpose_mask:
            return await self._find_document_by_purpose_mask(
                payment=payment,
                document_type=DocumentType.demand,
                payment_purpose_mask=payment_purpose_mask,
                prioritize_oldest=prioritize_oldest,
            )

        return None

    async def _find_document_by_purpose_mask(
        self,
        payment,
        document_type: DocumentType,
        payment_purpose_mask: str | None,
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
                    moment=moment,
                    prioritize_oldest=prioritize_oldest,
                )

            if document_type == DocumentType.invoiceout:
                return await self.invoiceout_service.find_by_name_and_agent(
                    name=name,
                    agent_id=payment.agent_id,
                    moment=moment,
                    prioritize_oldest=prioritize_oldest,
                )

            if document_type == DocumentType.demand:
                return await self.demand_service.find_by_name_and_agent(
                    name=name,
                    agent_id=payment.agent_id,
                    moment=moment,
                    prioritize_oldest=prioritize_oldest,
                )
        except (CustomerOrderNotFoundError, InvoiceOutNotFoundError, DemandNotFoundError):
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
