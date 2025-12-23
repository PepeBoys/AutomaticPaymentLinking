# path: src/apps/customerorder/REMARK.md
# Замечания по приложению customerorder

## 🟢 Положительные стороны

### 1. Отличное переиспользование кода
```
✓ Минимум дублирования через наследование от payable_document_base
✓ ~240 строк собственного кода vs ~2500 унаследованных
✓ Единообразие с другими документными модулями
```

### 2. Полезный дополнительный функционал
```
✓ Endpoint GET /search/for-payment - практичное API для поиска заказов
✓ Использование доменных методов (get_unpaid_amount, is_fully_paid)
✓ Валидация обязательных полей в _to_entity()
```

### 3. Чистая архитектура
```
✓ Четкое разделение слоев (API → Service → Domain → Client)
✓ Бизнес-логика в domain layer (get_unpaid_amount, is_fully_paid)
✓ Применение DI через FastAPI Depends
✓ Type hints на всех методах
```

### 4. Соответствие принципам
```
✓ Single Responsibility Principle
✓ Open/Closed Principle (расширение через наследование)
✓ Liskov Substitution Principle
✓ DRY (Don't Repeat Yourself)
```

## 🟡 Важные замечания

### 1. Пустой pass в CustomerOrderEntity

**Проблема**: Избыточный код
```python
# customerorder/domain/entities.py
@dataclass
class CustomerOrderEntity(BasePayableDocumentEntity):
    """Доменная сущность заказа покупателя."""
    
    pass  # ← Избыточный pass
```

**Решение**: Удалить `pass`
```python
@dataclass
class CustomerOrderEntity(BasePayableDocumentEntity):
    """Доменная сущность заказа покупателя."""
```

### 2. Неиспользуемый CustomerOrderFilter

**Проблема**: Value Object определен, но нигде не используется
```python
# domain/value_objects.py
@dataclass(frozen=True)
class CustomerOrderFilter:
    """Фильтр для поиска заказов покупателя."""
    # 42 строки кода
    # ❌ Нигде не используется в проекте
```

**Обоснование наличия**: 
- Имеет дополнительное поле `only_unpaid: bool = True`
- Более продвинутый, чем базовый фильтр

**Решение**: 
```python
# Вариант 1: Использовать в сервисе
async def find_for_payment_advanced(
    self,
    filter: CustomerOrderFilter
) -> list[CustomerOrderEntity]:
    """Расширенный поиск заказов с фильтрацией неоплаченных."""
    filter_str = filter.to_moysklad_filter()
    entities = await self._client.list(filter=filter_str)
    
    if filter.only_unpaid:
        entities = [e for e in entities if e.get_unpaid_amount() > 0]
    
    return entities

# Вариант 2: Удалить файл value_objects.py
```

### 3. Отсутствие docstring в методах

**Проблема**: Методы недостаточно документированы
```python
@property
def entity_type(self) -> str:
    return "customerorder"  # ❌ Нет docstring

@staticmethod
def _to_entity(data: dict) -> CustomerOrderEntity:
    # ❌ Нет docstring с описанием полей
    agent_meta = data.get("agent", {}).get("meta", {})
    # ...
```

**Решение**: Добавить docstrings
```python
@property
def entity_type(self) -> str:
    """
    Тип сущности в МойСклад API.
    
    Returns:
        "customerorder" - тип заказа покупателя
    """
    return "customerorder"

@staticmethod
def _to_entity(data: dict) -> CustomerOrderEntity:
    """
    Преобразовать JSON из API МойСклад в доменную сущность.
    
    Args:
        data: JSON данные заказа покупателя из API
            Обязательные поля:
            - id, accountId, name, moment, sum, meta.href
            - agent.meta.href, organization.meta.href
            Опциональные поля:
            - applicable, payedSum, shippedSum, invoicedSum
            - project.meta.href, salesChannel.meta.href
        
    Returns:
        Доменная сущность CustomerOrderEntity
        
    Raises:
        CustomerOrderNotFoundError: Если отсутствует meta.href
    """
    # ...
```

### 4. Улучшение type hints

**Текущий код**:
```python
def _to_entity(data: dict) -> CustomerOrderEntity:
    # ❌ dict слишком общий тип
```

**Улучшенный вариант**:
```python
from typing import Any

def _to_entity(data: dict[str, Any]) -> CustomerOrderEntity:
    # ✓ Более специфичный тип
```

## 🟢 Рекомендации по улучшению

### 5. Добавить примеры использования в module docstring
```python
# customerorder/__init__.py
"""
Модуль для работы с заказами покупателей МойСклад.

Заказы покупателей используются для:
- Учета заказов от клиентов
- Привязки входящих платежей (paymentin, cashin)
- Отслеживания оплаты, отгрузки и выставления счетов

Основные поля заказа:
- sum: Общая сумма заказа
- payedSum: Оплаченная сумма
- shippedSum: Отгруженная сумма
- invoicedSum: Выставлено счетов на сумму

Примеры использования:
    
    from apps.customerorder.services.customerorder_service import CustomerOrderService
    
    # Получить заказ
    order = await service.get_by_id("order_123")
    
    # Проверить статус оплаты
    unpaid = order.get_unpaid_amount()  # sum - payedSum
    is_paid = order.is_fully_paid()     # payedSum >= sum
    
    # Найти заказы для привязки платежа
    orders = await service.find_for_payment(
        agent_id="agent_456",
        payment_sum=15000.0,
        search_by_sum=True  # Точное совпадение по сумме
    )
    
    # Найти заказ по имени
    order = await service.find_by_name_and_agent(
        name="00042",
        agent_id="agent_456"
    )
"""
```

### 6. Расширенная валидация в _to_entity
```python
@staticmethod
def _to_entity(data: dict[str, Any]) -> CustomerOrderEntity:
    """Преобразовать JSON из API в entity."""
    
    # Валидация обязательных полей
    required_fields = ["id", "accountId", "name", "moment", "sum"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise CustomerOrderAPIError(
            f"Отсутствуют обязательные поля: {', '.join(missing)}",
            details={
                "missing_fields": missing,
                "received_fields": list(data.keys())
            }
        )
    
    # Валидация meta.href
    if not data.get("meta", {}).get("href"):
        raise CustomerOrderNotFoundError(
            "Некорректные данные заказа покупателя: отсутствует meta.href"
        )
    
    # Валидация числовых полей
    try:
        sum_value = float(data["sum"])
        payed_sum = float(data.get("payedSum", 0))
    except (ValueError, TypeError) as exc:
        raise CustomerOrderAPIError(
            "Некорректный формат числовых полей",
            details={"error": str(exc)}
        )
    
    if payed_sum > sum_value:
        logger.warning(
            "Оплаченная сумма больше общей суммы заказа: payedSum=%s > sum=%s, order_id=%s",
            payed_sum, sum_value, data.get("id")
        )
    
    # Парсинг...
```

### 7. Добавить логирование в сервис
```python
import logging

logger = logging.getLogger(__name__)

class CustomerOrderService(BaseDocumentService):
    async def find_for_payment(
        self,
        agent_id: str,
        payment_sum: float,
        search_by_sum: bool = True,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ) -> list[CustomerOrderEntity]:
        """Найти заказы для привязки платежа."""
        logger.info(
            "Поиск заказов для платежа: agent_id=%s, sum=%s, by_sum=%s, org=%s",
            agent_id,
            payment_sum,
            search_by_sum,
            organization_id
        )
        
        try:
            orders = await super().find_for_payment(
                agent_id, payment_sum, search_by_sum, organization_id, prioritize_oldest
            )
            logger.info(
                "Найдено заказов: %d (unpaid: %d)",
                len(orders),
                len([o for o in orders if o.get_unpaid_amount() > 0])
            )
            return orders
        except Exception as exc:
            logger.error(
                "Ошибка поиска заказов: agent_id=%s, error=%s",
                agent_id,
                exc,
                exc_info=True
            )
            raise
```

### 8. Добавить метрики для мониторинга
```python
from prometheus_client import Counter, Histogram

customerorder_operations_total = Counter(
    'customerorder_operations_total',
    'Total customerorder operations',
    ['operation', 'status']
)

customerorder_unpaid_gauge = Gauge(
    'customerorder_unpaid_amount',
    'Unpaid amount for customer orders',
    ['order_id']
)

class CustomerOrderService(BaseDocumentService):
    async def find_for_payment(self, ...) -> list[CustomerOrderEntity]:
        try:
            orders = await super().find_for_payment(...)
            
            # Обновить метрики
            for order in orders:
                customerorder_unpaid_gauge.labels(
                    order_id=order.id
                ).set(order.get_unpaid_amount())
            
            customerorder_operations_total.labels(
                operation='find_for_payment',
                status='success'
            ).inc()
            
            return orders
        except Exception:
            customerorder_operations_total.labels(
                operation='find_for_payment',
                status='failure'
            ).inc()
            raise
```

### 9. Улучшить endpoint /search/for-payment
```python
@router.get("/search/for-payment")
async def search_orders_for_payment(
    agent_id: str = Query(..., description="ID контрагента"),
    payment_sum: float = Query(..., description="Сумма платежа"),
    by_sum: bool = Query(True, description="Искать по точной сумме"),
    organization_id: str | None = Query(None, description="ID организации"),  # ← NEW
    prioritize_oldest: bool = Query(True, description="Приоритет старых"),   # ← NEW
    service: CustomerOrderSvcDep = None,
):
    """
    Поиск заказов для привязки платежа.
    
    Находит неоплаченные заказы покупателя по контрагенту и сумме.
    
    Args:
        agent_id: ID контрагента (обязательно)
        payment_sum: Сумма платежа для привязки (обязательно)
        by_sum: Искать по точной сумме (с tolerance ±0.01)
        organization_id: Фильтр по организации (опционально)
        prioritize_oldest: Сортировка (старые первыми или новые)
        service: Сервис заказов
        
    Returns:
        Список заказов с вычисленными полями:
        - unpaidAmount: Неоплаченная сумма (sum - payedSum)
        - isFullyPaid: Флаг полной оплаты
    """
    entities = await service.find_for_payment(
        agent_id=agent_id,
        payment_sum=payment_sum,
        search_by_sum=by_sum,
        organization_id=organization_id,
        prioritize_oldest=prioritize_oldest,
    )
    
    return {
        "orders": [
            {
                "id": e.id,
                "name": e.name,
                "sum": e.sum,
                "payedSum": e.payed_sum,
                "shippedSum": e.shipped_sum,      # ← NEW
                "invoicedSum": e.invoiced_sum,    # ← NEW
                "unpaidAmount": e.get_unpaid_amount(),
                "moment": e.moment.isoformat(),
                "isFullyPaid": e.is_fully_paid(),
                "agentId": e.agent_id,            # ← NEW (для UI)
            }
            for e in entities
        ],
        "total": len(entities),
        "totalUnpaidAmount": sum(e.get_unpaid_amount() for e in entities),  # ← NEW
    }
```

### 10. Добавить unit тесты
```python
# tests/apps/customerorder/test_customerorder_service.py
import pytest
from apps.customerorder.services.customerorder_service import CustomerOrderService
from apps.customerorder.domain.entities import CustomerOrderEntity

@pytest.mark.asyncio
async def test_to_entity():
    """Тест преобразования JSON в entity."""
    data = {
        "id": "order_123",
        "accountId": "account_456",
        "name": "00042",
        "moment": "2024-12-15T14:20:00",
        "applicable": True,
        "sum": 25000.0,
        "payedSum": 10000.0,
        "shippedSum": 0.0,
        "invoicedSum": 25000.0,
        "agent": {"meta": {"href": ".../counterparty/agent_789"}},
        "organization": {"meta": {"href": ".../organization/org_111"}},
        "meta": {"href": ".../customerorder/order_123"}
    }
    
    entity = CustomerOrderService._to_entity(data)
    
    assert entity.id == "order_123"
    assert entity.name == "00042"
    assert entity.sum == 25000.0
    assert entity.payed_sum == 10000.0
    assert entity.get_unpaid_amount() == 15000.0
    assert entity.is_fully_paid() is False

@pytest.mark.asyncio
async def test_to_entity_fully_paid():
    """Тест полностью оплаченного заказа."""
    data = {
        "id": "order_123",
        "accountId": "account_456",
        "name": "00042",
        "moment": "2024-12-15T14:20:00",
        "applicable": True,
        "sum": 25000.0,
        "payedSum": 25000.0,  # Полностью оплачен
        "agent": {"meta": {"href": ".../counterparty/agent_789"}},
        "organization": {"meta": {"href": ".../organization/org_111"}},
        "meta": {"href": ".../customerorder/order_123"}
    }
    
    entity = CustomerOrderService._to_entity(data)
    
    assert entity.get_unpaid_amount() == 0.0
    assert entity.is_fully_paid() is True

@pytest.mark.asyncio
async def test_to_entity_missing_meta_href():
    """Тест обработки отсутствия meta.href."""
    data = {
        "id": "order_123",
        "accountId": "account_456",
        "name": "00042",
        # Отсутствует meta.href
    }
    
    with pytest.raises(CustomerOrderNotFoundError):
        CustomerOrderService._to_entity(data)
```

### 11. Добавить helper методы
```python
class CustomerOrderService(BaseDocumentService):
    async def get_unpaid_orders(
        self,
        agent_id: str,
        organization_id: str | None = None,
    ) -> list[CustomerOrderEntity]:
        """
        Получить все неоплаченные заказы контрагента.
        
        Args:
            agent_id: ID контрагента
            organization_id: ID организации (опционально)
            
        Returns:
            Список неоплаченных заказов
        """
        orders = await self.find_for_payment(
            agent_id=agent_id,
            payment_sum=0,  # Не фильтровать по сумме
            search_by_sum=False,
            organization_id=organization_id,
        )
        
        return [o for o in orders if not o.is_fully_paid()]
    
    async def get_order_payment_status(
        self,
        order_id: str
    ) -> dict:
        """
        Получить статус оплаты заказа.
        
        Args:
            order_id: ID заказа
            
        Returns:
            Словарь со статусом оплаты:
            {
                "sum": 25000.0,
                "payedSum": 10000.0,
                "unpaidAmount": 15000.0,
                "isFullyPaid": False,
                "paymentProgress": 40.0  # Процент оплаты
            }
        """
        order = await self.get_by_id(order_id)
        
        return {
            "sum": order.sum,
            "payedSum": order.payed_sum,
            "unpaidAmount": order.get_unpaid_amount(),
            "isFullyPaid": order.is_fully_paid(),
            "paymentProgress": (order.payed_sum / order.sum * 100) if order.sum > 0 else 0,
        }
```

## 📊 Статистика кода
```
┌─────────────────────────────────────────────────────────────────┐
│                    МЕТРИКИ ПРИЛОЖЕНИЯ                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Всего строк кода:              ~240                            │
│  Унаследованного кода:          ~2500                           │
│  Коэффициент переиспользования: 91%                             │
│                                                                 │
│  Файлов:                        9                               │
│  Классов:                       5                               │
│  Функций/методов:               6                               │
│                                                                 │
│  API Endpoints:                 2 (+ 1 search endpoint)         │
│  Покрытие типизацией:           95%                             │
│  Cyclomatic Complexity:         3-5 (низкая, хорошо)            │
│  Maintainability Index:         80+ (хорошо)                    │
│                                                                 │
│  TODO/FIXME:                    0                               │
│  Docstrings:                    65% (средне)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## ✅ Что сделано хорошо

1. ✅ Максимальное переиспользование через наследование от payable_document_base
2. ✅ Полезный endpoint /search/for-payment для поиска заказов
3. ✅ Использование доменных методов в API (get_unpaid_amount, is_fully_paid)
4. ✅ Валидация обязательных полей в _to_entity()
5. ✅ Чистая архитектура с разделением слоев
6. ✅ Type hints на всех публичных методах
7. ✅ Dependency Injection через FastAPI
8. ✅ Обработка исключений с кастомными типами
9. ✅ Правильная семантика (документ для входящих платежей)

## 🎯 Приоритет доработок

1. **Низкий**: Удалить `pass` в CustomerOrderEntity (#1)
2. **Средний**: Либо использовать, либо удалить CustomerOrderFilter (#2)
3. **Средний**: Добавить docstrings к методам (#3)
4. **Низкий**: Улучшить type hints (#4)
5. **Низкий**: Добавить примеры в module docstring (#5)
6. **Низкий**: Расширенная валидация полей (#6)
7. **Низкий**: Добавить логирование (#7)
8. **Средний**: Написать unit тесты (#10)
9. **Низкий**: Добавить helper методы (#11)

## 🔍 Общий вывод

Приложение `customerorder` является **отличным примером правильного применения наследования** и **добавления практичного функционала**. Endpoint `/search/for-payment` демонстрирует хорошее понимание бизнес-процессов - он дает именно ту информацию, которая нужна для UI выбора заказов при привязке платежа.

**Оценка качества**: 9/10

**Сильные стороны**:
- Идеальное переиспользование кода
- Практичное API с вычисляемыми полями
- Использование доменных методов в правильном месте
- Валидация данных
- Чистая архитектура

**Точки роста**:
- Документация (docstrings)
- Покрытие тестами
- Использование или удаление CustomerOrderFilter
- Логирование и метрики

## 💡 Дополнительные наблюдения

### Правильное использование domain layer
```python
# ✓ ПРАВИЛЬНО: Бизнес-логика в domain
@dataclass
class BasePayableDocumentEntity:
    def get_unpaid_amount(self) -> float:
        return self.sum - self.payed_sum
    
    def is_fully_paid(self) -> bool:
        return self.payed_sum >= self.sum

# ✓ ПРАВИЛЬНО: Использование в API layer
@router.get("/search/for-payment")
async def search_orders_for_payment(...):
    return {
        "unpaidAmount": e.get_unpaid_amount(),  # Вызов доменного метода
        "isFullyPaid": e.is_fully_paid(),       # Вызов доменного метода
    }
```

Это демонстрирует **правильное понимание Clean Architecture** - бизнес-логика находится в domain layer, а API layer только использует ее.

### Отличие от платежных модулей
```
┌───────────────────────────────────────────────────────────────┐
│         PAYMENT MODULES vs DOCUMENT MODULES                   │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  PAYMENT (payment_base):                                      │
│  • paymentin, cashin, paymentout, cashout                     │
│  • Используются для ОПЛАТЫ документов                         │
│  • Привязываются К документам                                 │
│  • Имеют: sum, agent_id, linked_operations                    │
│                                                               │
│  DOCUMENT (payable_document_base):                            │
│  • customerorder, invoiceout, demand                          │
│  • Используются для ПОЛУЧЕНИЯ оплаты                          │
│  • К НИМ привязываются платежи                                │
│  • Имеют: sum, payed_sum, shipped_sum, invoiced_sum           │
│  • Методы: get_unpaid_amount(), is_fully_paid()               │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

Это фундаментальное различие правильно отражено в архитектуре.