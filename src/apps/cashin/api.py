"""API эндпоинты для работы с приходными ордерами."""

import logging

from fastapi import APIRouter

from .dependencies import CashInSvcDep
from .schemas import CashInResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{payment_id}", response_model=CashInResponse)
async def get_cashin(
    payment_id: str,
    service: CashInSvcDep,
):
    """
    Получить приходный ордер по ID.
    
    Args:
        payment_id: ID платежа в МойСклад
        service: Сервис платежей
        
    Returns:
        Информация о приходном ордере
    """
    entity = await service.get_by_id(payment_id)

    return CashInResponse(
        id=entity.id,
        accountId=entity.account_id,
        name=entity.name,
        moment=entity.moment,
        applicable=entity.applicable,
        sum=entity.sum,
        agent={"meta": {"href": f"entity/counterparty/{entity.agent_id}", "type": "counterparty"}},
        organization={"meta": {"href": f"entity/organization/{entity.organization_id}", "type": "organization"}},
        paymentPurpose=entity.payment_purpose,
        operations=[
            {
                "meta": op["meta"],
                "linkedSum": op.get("linkedSum"),
            }
            for op in entity.linked_operations
        ],
        meta={"href": entity.meta_href, "type": "cashin"},
    )