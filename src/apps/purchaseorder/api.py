"""API эндпоинты для работы с заказами покупателя."""

import logging

from fastapi import APIRouter, Query

from .dependencies import PurchaseOrderSvcDep
from .schemas import PurchaseOrderResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{order_id}", response_model=PurchaseOrderResponse)
async def get_purchaseorder(
    order_id: str,
    service: PurchaseOrderSvcDep,
):
    """
    Получить заказ покупателя по ID.
    
    Args:
        order_id: ID заказа в МойСклад
        service: Сервис заказов
        
    Returns:
        Информация о заказе
    """
    entity = await service.get_by_id(order_id)
    
    return PurchaseOrderResponse(
        id=entity.id,
        accountId=entity.account_id,
        name=entity.name,
        moment=entity.moment,
        applicable=entity.applicable,
        sum=entity.sum,
        payedSum=entity.payed_sum,
        shippedSum=entity.shipped_sum,
        invoicedSum=entity.invoiced_sum,
        agent={"meta": {"href": f"entity/counterparty/{entity.agent_id}", "type": "counterparty"}},
        organization={"meta": {"href": f"entity/organization/{entity.organization_id}", "type": "organization"}},
        meta={"href": entity.meta_href, "type": "purchaseorder"},
    )


@router.get("/search/for-payment")
async def search_orders_for_payment(
    agent_id: str = Query(..., description="ID контрагента"),
    payment_sum: float = Query(..., description="Сумма платежа"),
    by_sum: bool = Query(True, description="Искать по точной сумме"),
    service: PurchaseOrderSvcDep = None,
):
    """
    Поиск заказов для привязки платежа.
    
    Args:
        agent_id: ID контрагента
        payment_sum: Сумма платежа
        by_sum: Искать по точной сумме
        service: Сервис заказов
        
    Returns:
        Список подходящих заказов
    """
    entities = await service.find_for_payment(
        agent_id=agent_id,
        payment_sum=payment_sum,
        search_by_sum=by_sum,
    )
    
    return {
        "orders": [
            {
                "id": e.id,
                "name": e.name,
                "sum": e.sum,
                "payedSum": e.payed_sum,
                "unpaidAmount": e.get_unpaid_amount(),
                "moment": e.moment.isoformat(),
                "isFullyPaid": e.is_fully_paid(),
            }
            for e in entities
        ],
        "total": len(entities),
    }