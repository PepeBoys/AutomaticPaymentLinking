"""API эндпоинты для работы с входящими платежами."""

import logging

from fastapi import APIRouter

from .dependencies import PaymentOutSvcDep
from .schemas import PaymentOutResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{payment_id}", response_model=PaymentOutResponse)
async def get_paymentout(
    payment_id: str,
    service: PaymentOutSvcDep,
):
    """
    Получить входящий платеж по ID.
    
    Args:
        payment_id: ID платежа в МойСклад
        service: Сервис платежей
        
    Returns:
        Информация о платеже
    """
    entity = await service.get_by_id(payment_id)
    
    return PaymentOutResponse(
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
        meta={"href": entity.meta_href, "type": "paymentout"},
    )