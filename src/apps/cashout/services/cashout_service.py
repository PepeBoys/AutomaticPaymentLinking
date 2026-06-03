"""Сервис для работы с расходными ордерами."""

import logging

from ...ms_auth.services.auth_service import MySkladAuthService
from ...payment_base.services.base_client import BasePaymentClient
from ...payment_base.services.base_service import BasePaymentService
from ..domain.entities import CashOutEntity
from .cashout_client import CashOutClient

logger = logging.getLogger(__name__)


class CashOutService(BasePaymentService[CashOutEntity, BasePaymentClient]):
    """Сервис для работы с расходными ордерами."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        super().__init__(auth_service, CashOutClient(auth_service))

    @property
    def entity_type(self) -> str:
        return "cashout"

    @staticmethod
    def _to_entity(data: dict) -> CashOutEntity:
        agent_meta = data.get("agent", {}).get("meta", {})
        agent_href = agent_meta.get("href", "")
        agent_id = agent_href.split("/")[-1] if agent_href else ""

        org_meta = data.get("organization", {}).get("meta", {})
        org_href = org_meta.get("href", "")
        org_id = org_href.split("/")[-1] if org_href else ""

        project_meta = data.get("project", {}).get("meta", {})
        project_href = project_meta.get("href") if project_meta else None

        sales_channel_meta = data.get("salesChannel", {}).get("meta", {})
        sales_channel_href = (
            sales_channel_meta.get("href") if sales_channel_meta else None
        )

        expense_item_meta = data.get("expenseItem", {}).get("meta", {})
        expense_item_href = expense_item_meta.get("href") if expense_item_meta else None

        linked_ops = [
            {
                "meta": {
                    "href": op.get("meta", {}).get("href", ""),
                    "type": op.get("meta", {}).get("type", ""),
                },
                "linkedSum": op.get("linkedSum", 0),
            }
            for op in data.get("operations", [])
        ]

        return CashOutEntity(
            id=data["id"],
            account_id=data["accountId"],
            name=data["name"],
            moment=data["moment"],
            applicable=data["applicable"],
            sum=data["sum"],
            agent_id=agent_id,
            organization_id=org_id,
            payment_purpose=data.get("paymentPurpose"),
            linked_operations=linked_ops,
            meta_href=data["meta"]["href"],
            project_meta_href=project_href,
            sales_channel_meta_href=sales_channel_href,
            expense_item_meta_href=expense_item_href,
        )
