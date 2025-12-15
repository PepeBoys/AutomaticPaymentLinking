"""Сервис для работы со счетами покупателю."""

import logging
from datetime import datetime
from typing import Optional

from ...ms_auth.services.auth_service import MySkladAuthService
from ...payable_document_base.services.base_client import BaseDocumentClient
from ...payable_document_base.services.base_service import BaseDocumentService
from ..domain.entities import InvoiceOutEntity
from ..exceptions import InvoiceOutNotFoundError
from .invoiceout_client import InvoiceOutClient

logger = logging.getLogger(__name__)


class InvoiceOutService(BaseDocumentService[InvoiceOutEntity, BaseDocumentClient]):
    """Сервис для работы со счетами покупателю."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        super().__init__(auth_service, InvoiceOutClient(auth_service))

    @property
    def entity_type(self) -> str:
        return "invoiceout"

    @staticmethod
    def _to_entity(data: dict) -> InvoiceOutEntity:
        agent_meta = data.get("agent", {}).get("meta", {})
        agent_href = agent_meta.get("href", "")
        agent_id = agent_href.split("/")[-1] if agent_href else ""

        org_meta = data.get("organization", {}).get("meta", {})
        org_href = org_meta.get("href", "")
        org_id = org_href.split("/")[-1] if org_href else ""

        project_meta = data.get("project", {}).get("meta", {})
        project_href = project_meta.get("href") if project_meta else None

        if not data.get("meta", {}).get("href"):
            raise InvoiceOutNotFoundError("Некорректные данные счета покупателю")

        return InvoiceOutEntity(
            id=data["id"],
            account_id=data["accountId"],
            name=data["name"],
            moment=data["moment"],
            applicable=data.get("applicable", False),
            sum=data["sum"],
            payed_sum=data.get("payedSum", 0),
            agent_id=agent_id,
            organization_id=org_id,
            meta_href=data["meta"]["href"],
            project_meta_href=project_href,
        )
