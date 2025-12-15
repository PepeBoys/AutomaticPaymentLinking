"""Сервис для работы со счетами поставщиков."""

import logging
from typing import Optional
from datetime import datetime

from ...ms_auth.services.auth_service import MySkladAuthService
from ..domain.entities import InvoiceInEntity
from ..exceptions import InvoiceInNotFoundError
from ..payable_document_base.services.base_client import BaseDocumentClient
from ..payable_document_base.services.base_service import BaseDocumentService
from .invoicein_client import InvoiceInClient

logger = logging.getLogger(__name__)


class InvoiceInService(BaseDocumentService[InvoiceInEntity, BaseDocumentClient]):
    """Сервис для работы со счетами поставщиков."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        super().__init__(auth_service, InvoiceInClient(auth_service))

    @property
    def entity_type(self) -> str:
        return "invoicein"

    @staticmethod
    def _to_entity(data: dict) -> InvoiceInEntity:
        agent_meta = data.get("agent", {}).get("meta", {})
        agent_href = agent_meta.get("href", "")
        agent_id = agent_href.split("/")[-1] if agent_href else ""

        org_meta = data.get("organization", {}).get("meta", {})
        org_href = org_meta.get("href", "")
        org_id = org_href.split("/")[-1] if org_href else ""

        project_meta = data.get("project", {}).get("meta", {})
        project_href = project_meta.get("href") if project_meta else None

        if not data.get("meta", {}).get("href"):
            raise InvoiceInNotFoundError("Некорректные данные счета поставщика")

        return InvoiceInEntity(
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
