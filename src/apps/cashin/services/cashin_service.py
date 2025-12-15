"""Сервис для работы с приходными ордерами."""

import logging

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import CashInEntity
from ..payment_base.services.base_client import BasePaymentClient
from ..payment_base.services.base_service import BasePaymentService
from .cashin_client import CashInClient

logger = logging.getLogger(__name__)


class CashInService(BasePaymentService[CashInEntity, BasePaymentClient]):
    """Сервис для работы с приходными ордерами."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        super().__init__(auth_service, CashInClient(auth_service))

    @property
    def entity_type(self) -> str:
        return "cashin"

    @staticmethod
    def _to_entity(data: dict) -> CashInEntity:
        agent_meta = data.get("agent", {}).get("meta", {})
        agent_href = agent_meta.get("href", "")
        agent_id = agent_href.split("/")[-1] if agent_href else ""

        org_meta = data.get("organization", {}).get("meta", {})
        org_href = org_meta.get("href", "")
        org_id = org_href.split("/")[-1] if org_href else ""

        project_meta = data.get("project", {}).get("meta", {})
        project_href = project_meta.get("href") if project_meta else None

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

        return CashInEntity(
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
        )
