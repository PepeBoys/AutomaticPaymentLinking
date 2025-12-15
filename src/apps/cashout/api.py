"""API эндпоинты для работы с расходными ордерами."""

import logging

from fastapi import APIRouter

from .dependencies import CashOutSvcDep
from .schemas import CashOutResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{payment_id}", response_model=CashOutResponse)
async def get_cashout(
    payment_id: str,
    service: CashOutSvcDep,
):
    """
    Получить расходный ордер по ID.
    
    Args:
        payment_id: ID платежа в МойСклад
        service: Сервис платежей

    Returns:
        Информация о расходном ордере
    """
    entity = await service.get_by_id(payment_id)

    return CashOutResponse(
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
        meta={"href": entity.meta_href, "type": "cashout"},
    )