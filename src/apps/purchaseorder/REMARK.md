# Замечания по приложению purchaseorder

## 🟢 Положительные стороны

### 1. Отличное переиспользование кода
```
✓ Собственный код: ~120 строк
✓ Унаследованный код: ~900 строк
✓ Коэффициент переиспользования: 88%
✓ Минимум дублирования с payable_document_base
✓ Правильное применение наследования
```

### 2. REST API с двумя endpoints
```
✓ GET /{order_id} - получение заказа
✓ GET /search/for-payment - поиск для привязки
✓ Domain методы используются в API (unpaidAmount, isFullyPaid)
✓ Полезный endpoint для webhook обработки
```

### 3. Domain методы работают
```
✓ is_fully_paid() - проверка полной оплаты
✓ get_unpaid_amount() - расчет долга
✓ is_partially_paid() - проверка частичной оплаты
✓ get_unshipped_amount() - контроль отгрузки
✓ get_uninvoiced_amount() - контроль счетов
```

## 🔴 КРИТИЧЕСКИЕ замечания

### 1. Copy-paste ошибки в docstrings! 🚨

**ПРОБЛЕМА**: В 3 файлах docstrings говорят о заказах **ПОКУПАТЕЛЯ**, хотя это заказы **ПОСТАВЩИКАМ**!
```python
# api.py - строка 1
"""API эндпоинты для работы с заказами покупателя."""
# ❌ ОШИБКА! Должно быть: "заказами поставщикам"

# dependencies.py - строка 1
"""Dependency Injection для заказов покупателя."""
# ❌ ОШИБКА! Должно быть: "заказов поставщикам"

# dependencies.py - строка 13-14
"""
Получить сервис заказов покупателя.
"""
# ❌ ОШИБКА! Должно быть: "заказов поставщикам"

# value_objects.py - строка 1
"""Value Objects для заказов покупателя."""
# ❌ ОШИБКА! Должно быть: "заказов поставщикам"

# value_objects.py - строка 9
"""Фильтр для поиска заказов покупателя (Value Object)."""
# ❌ ОШИБКА! Должно быть: "заказов поставщикам"

# api.py - строка 18-19
"""
Получить заказ покупателя по ID.
"""
# ❌ ОШИБКА! Должно быть: "заказ поставщику по ID"
```

**Это классический случай copy-paste из customerorder без проверки!**

Очевидно что модуль был скопирован из `customerorder` и docstrings не обновили.

**Решение**: Исправить все docstrings
```python
# api.py
"""API эндпоинты для работы с заказами поставщикам."""

@router.get("/{order_id}", response_model=PurchaseOrderResponse)
async def get_purchaseorder(order_id: str, service: PurchaseOrderSvcDep):
    """
    Получить заказ поставщику по ID.
    
    ВАЖНО: Заказ поставщику = заказ НА ЗАКУПКУ товаров у поставщика.
    """

# dependencies.py
"""Dependency Injection для заказов поставщикам."""

async def get_purchaseorder_service(...) -> PurchaseOrderService:
    """Получить сервис заказов поставщикам."""

# value_objects.py
"""Value Objects для заказов поставщикам."""

@dataclass(frozen=True)
class PurchaseOrderFilter:
    """Фильтр для поиска заказов поставщикам (Value Object)."""
```

### 2. 100% дублирование _to_entity с customerorder

**ПРОБЛЕМА**: Код _to_entity идентичен на 100% с customerorder
```python
# purchaseorder/services/purchaseorder_service.py
@staticmethod
def _to_entity(data: dict) -> PurchaseOrderEntity:
    agent_meta = data.get("agent", {}).get("meta", {})
    agent_href = agent_meta.get("href", "")
    agent_id = agent_href.split("/")[-1] if agent_href else ""
    # ... точно такой же код как в customerorder

# customerorder/services/customerorder_service.py
@staticmethod
def _to_entity(data: dict) -> CustomerOrderEntity:
    agent_meta = data.get("agent", {}).get("meta", {})
    agent_href = agent_meta.get("href", "")
    agent_id = agent_href.split("/")[-1] if agent_href else ""
    # ... точно такой же код!
```

**Дублирование**: ~55 строк идентичного кода в 2 модулях

**Решение**: Вынести в BaseDocumentService
```python
# payable_document_base/services/base_service.py
class BaseDocumentService(Generic[TEntity, TClient], ABC):
    @staticmethod
    def _parse_document_data(data: dict) -> dict:
        """
        Парсить общие поля документа из JSON МойСклад.
        
        Returns:
            Dict с распарсенными полями:
            {
                "agent_id": str,
                "organization_id": str,
                "project_meta_href": str | None,
                "sales_channel_meta_href": str | None,
            }
        """
        from ...payable_document_base.exceptions import DocumentAPIError
        
        # Парсинг agent_id
        agent_href = data.get("agent", {}).get("meta", {}).get("href")
        if not agent_href:
            raise DocumentAPIError("Missing agent.meta.href in document data")
        agent_id = agent_href.split("/")[-1]
        
        # Парсинг organization_id
        org_href = data.get("organization", {}).get("meta", {}).get("href")
        if not org_href:
            raise DocumentAPIError("Missing organization.meta.href in document data")
        org_id = org_href.split("/")[-1]
        
        # Парсинг project
        project_meta = data.get("project", {}).get("meta", {})
        project_href = project_meta.get("href") if project_meta else None
        
        # Парсинг salesChannel
        sales_channel_meta = data.get("salesChannel", {}).get("meta", {})
        sales_channel_href = sales_channel_meta.get("href") if sales_channel_meta else None
        
        return {
            "agent_id": agent_id,
            "organization_id": org_id,
            "project_meta_href": project_href,
            "sales_channel_meta_href": sales_channel_href,
        }

# В purchaseorder и customerorder:
@staticmethod
def _to_entity(data: dict) -> PurchaseOrderEntity:
    """Преобразовать данные API в доменную сущность."""
    if not data.get("meta", {}).get("href"):
        raise PurchaseOrderNotFoundError("Некорректные данные заказа")
    
    parsed = BaseDocumentService._parse_document_data(data)
    
    return PurchaseOrderEntity(
        id=data["id"],
        account_id=data["accountId"],
        name=data["name"],
        moment=data["moment"],
        applicable=data.get("applicable", False),
        sum=data["sum"],
        payed_sum=data.get("payedSum", 0),
        shipped_sum=data.get("shippedSum"),
        invoiced_sum=data.get("invoicedSum"),
        meta_href=data["meta"]["href"],
        **parsed  # agent_id, organization_id, project_meta_href, ...
    )
```

### 3. PurchaseOrderFilter НЕ используется

**Проблема**: ~40 строк неиспользуемого кода
```python
# domain/value_objects.py - ~40 строк
class PurchaseOrderFilter:
    # ... сложная логика
    only_unpaid: bool = True  # Даже поле только для этого фильтра!
    
    def to_moysklad_filter(self) -> str:
        # ...

# ❌ НО: Нигде не используется!
# ❌ Сервис использует собственные методы поиска
# ❌ Не используется в find_for_payment()
```

**Решение**: Удалить файл или интегрировать в search

Рекомендация: **Удалить** `value_objects.py` или реализовать использование

### 4. Алиасы исключений - бессмысленные
```python
# exceptions.py
PurchaseOrderBaseException = BaseDocumentException  # ❌ Зачем?
PurchaseOrderAPIError = DocumentAPIError            # ❌ Зачем?
PurchaseOrderNotFoundError = DocumentNotFoundError  # ❌ Зачем?
```

**Решение**: Использовать базовые исключения напрямую

## 🟡 Важные замечания

### 5. Все проблемы из customerorder применимы

Поскольку код **идентичен**, все замечания из `customerorder/REMARK.md` актуальны:
```
✗ Парсинг ID через split("/")[-1] без валидации
✗ Отсутствие валидации обязательных полей в _to_entity
✗ Непоследовательность в получении Optional полей
✗ Логика форматирования в API endpoint
✗ Дублирование endpoint /search/for-payment
✗ Отсутствие unit тестов
```

### 6. Дублирование API endpoint с customerorder

**ПРОБЛЕМА**: API endpoint `/search/for-payment` идентичен в обоих модулях
```python
# purchaseorder/api.py
@router.get("/search/for-payment")
async def search_orders_for_payment(
    agent_id: str = Query(...),
    payment_sum: float = Query(...),
    by_sum: bool = Query(True),
    # ... 20+ строк кода

# customerorder/api.py
@router.get("/search/for-payment")
async def search_orders_for_payment(
    agent_id: str = Query(...),
    payment_sum: float = Query(...),
    by_sum: bool = Query(True),
    # ... точно такой же код!
```

**Дублирование**: ~25 строк идентичного кода

**Решение**: Создать базовую функцию или mixin
```python
# payable_document_base/api_utils.py (новый файл)
from typing import TypeVar, Generic
from apps.payable_document_base.services.base_service import BaseDocumentService

TService = TypeVar("TService", bound=BaseDocumentService)

def create_search_for_payment_response(entities: list) -> dict:
    """Создать стандартный ответ для /search/for-payment."""
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

# Использовать в purchaseorder и customerorder:
@router.get("/search/for-payment")
async def search_orders_for_payment(
    agent_id: str = Query(...),
    payment_sum: float = Query(...),
    by_sum: bool = Query(True),
    service: PurchaseOrderSvcDep = None,
):
    entities = await service.find_for_payment(
        agent_id=agent_id,
        payment_sum=payment_sum,
        search_by_sum=by_sum,
    )
    
    return create_search_for_payment_response(entities)
```

### 7. Проверка валидации в _to_entity

**ПОЛОЖИТЕЛЬНО**: В purchaseorder есть проверка meta.href!
```python
# purchaseorder/services/purchaseorder_service.py
if not data.get("meta", {}).get("href"):
    raise PurchaseOrderNotFoundError("Некорректные данные заказа поставщику")
    # ✓ Хорошо! Валидация есть
```

**НО**: customerorder не имеет такой проверки!

Это показывает **непоследовательность** между модулями.

**Решение**: Добавить эту проверку в BaseDocumentService._parse_document_data()

### 8. Отсутствие различий purchase vs customer

**ПРОБЛЕМА**: Нигде в коде не указано что это ЗАКАЗ ПОСТАВЩИКУ
```python
# Нет поля direction
class PurchaseOrderEntity(BasePayableDocumentEntity):
    pass  # Никак не отличается от CustomerOrderEntity!

# Только entity_type указывает на тип
entity_type = "purchaseorder"  # Единственное отличие
```

**Решение**: Добавить явное различие
```python
@dataclass
class PurchaseOrderEntity(BasePayableDocumentEntity):
    """Доменная сущность заказа поставщику."""
    
    @property
    def order_type(self) -> str:
        """Тип заказа."""
        return "purchase"
    
    @property
    def is_purchase_order(self) -> bool:
        """Проверить что это заказ поставщику (закупка)."""
        return True
    
    def __str__(self) -> str:
        return f"PurchaseOrder(id={self.id}, sum={self.sum}, from={self.agent_id})"

@dataclass
class CustomerOrderEntity(BasePayableDocumentEntity):
    """Доменная сущность заказа покупателя."""
    
    @property
    def order_type(self) -> str:
        """Тип заказа."""
        return "customer"
    
    @property
    def is_customer_order(self) -> bool:
        """Проверить что это заказ покупателя (продажа)."""
        return True
```

## 🟢 Рекомендации по улучшению

### 9. Исправить copy-paste ошибки (КРИТИЧНО!)
```diff
# api.py
-"""API эндпоинты для работы с заказами покупателя."""
+"""API эндпоинты для работы с заказами поставщикам."""

-    Получить заказ покупателя по ID.
+    Получить заказ поставщику по ID.

# dependencies.py
-"""Dependency Injection для заказов покупателя."""
+"""Dependency Injection для заказов поставщикам."""

-    """Получить сервис заказов покупателя."""
+    """Получить сервис заказов поставщикам."""

# value_objects.py
-"""Value Objects для заказов покупателя."""
+"""Value Objects для заказов поставщикам."""

-    """Фильтр для поиска заказов покупателя (Value Object)."""
+    """Фильтр для поиска заказов поставщикам (Value Object)."""
```

### 10. Вынести _to_entity в payable_document_base

См. решение в замечании #2

### 11. Вынести search_for_payment endpoint в базовый модуль

См. решение в замечании #6

### 12. Удалить неиспользуемый код
```bash
# Удалить PurchaseOrderFilter
rm src/apps/purchaseorder/domain/value_objects.py
```

### 13. Добавить различие purchase vs customer

См. решение в замечании #8

### 14. Добавить unit тесты
```python
# tests/apps/purchaseorder/test_service.py

def test_purchaseorder_type():
    """Тест что entity имеет правильный тип."""
    entity = PurchaseOrderEntity(...)
    
    assert entity.order_type == "purchase"
    assert entity.is_purchase_order is True

def test_purchaseorder_vs_customerorder():
    """Тест различий между purchaseorder и customerorder."""
    purchase_order = PurchaseOrderEntity(
        agent_id="supplier_123",  # Поставщик
        ...
    )
    
    customer_order = CustomerOrderEntity(
        agent_id="customer_456",  # Покупатель
        ...
    )
    
    assert purchase_order.order_type != customer_order.order_type
    assert purchase_order.is_purchase_order is True
    assert customer_order.is_customer_order is True

def test_search_for_payment_endpoint():
    """Тест endpoint поиска заказов для платежа."""
    response = client.get(
        "/purchaseorder/search/for-payment",
        params={
            "agent_id": "supplier_123",
            "payment_sum": 100000.0,
            "by_sum": True
        }
    )
    
    assert response.status_code == 200
    assert "orders" in response.json()
    assert "total" in response.json()

def test_domain_methods_in_api_response():
    """Тест что domain методы используются в API."""
    # Создать заказ с частичной оплатой
    order = PurchaseOrderEntity(
        sum=100000.0,
        payed_sum=60000.0,
        ...
    )
    
    # API должен вернуть результаты domain методов
    response = create_search_for_payment_response([order])
    
    assert response["orders"][0]["unpaidAmount"] == 40000.0
    assert response["orders"][0]["isFullyPaid"] is False
```

## 📊 Статистика кода
```
┌─────────────────────────────────────────────────────────────────┐
│                    МЕТРИКИ ПРИЛОЖЕНИЯ                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Всего строк кода:              ~200                            │
│                                                                 │
│  Собственный код:               ~120 строк                      │
│    • api.py:                    ~60 строк                       │
│    • purchaseorder_service.py:  ~55 строк (_to_entity)          │
│    • purchaseorder_client.py:   ~8 строк                        │
│    • value_objects.py:          ~40 строк (НЕ используется!)    │
│    • entities.py:               pass                            │
│    • schemas.py:                pass                            │
│    • exceptions.py:             алиасы                          │
│                                                                 │
│  Унаследованный код:            ~900 строк                      │
│  Коэффициент переиспользования: 88%                             │
│                                                                 │
│  Дублирование с customerorder:  100% (!)                        │
│    • _to_entity:                55 строк идентичны              │
│    • value_objects.py:          40 строк идентичны              │
│    • api.py /search/for-payment: 25 строк идентичны             │
│    • Всего дублирования:        ~120 строк                      │
│                                                                 │
│  Copy-paste ошибки:             6 docstrings                    │
│  Неиспользуемый код:            ~40 строк (PurchaseOrderFilter) │
│  Алиасов без функционала:       3 (исключения)                  │
│                                                                 │
│  REST endpoints:                2                               │
│  Domain методы используются:    Да (в API response)             │
│                                                                 │
│  Покрытие типизацией:           95%                             │
│  Cyclomatic Complexity:         3-4 (низкая)                    │
│  Maintainability Index:         85+ (очень хорошо)              │
│                                                                 │
│  TODO/FIXME:                    0                               │
│  Docstrings:                    50% (из них 6 с ошибками!)      │
│  Unit тесты:                    0                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## ✅ Что сделано хорошо

1. ✅ Отличное переиспользование кода (88%)
2. ✅ Два полезных REST endpoints
3. ✅ Domain методы используются в API
4. ✅ Проверка валидации meta.href в _to_entity
5. ✅ Правильное наследование
6. ✅ 5 domain методов работают корректно

## 🎯 Приоритет доработок

1. **КРИТИЧНО**: Исправить copy-paste ошибки в docstrings (#1)
2. **Высокий**: Вынести _to_entity в payable_document_base (#2)
3. **Высокий**: Вынести /search/for-payment в базовый модуль (#6)
4. **Высокий**: Удалить неиспользуемый PurchaseOrderFilter (#3)
5. **Средний**: Добавить различие purchase vs customer (#8, #13)
6. **Высокий**: Добавить unit тесты (#14)
7. **Средний**: Все проблемы из customerorder/REMARK.md (#5)
8. **Низкий**: Рассмотреть удаление алиасов исключений (#4)

## 🔍 Общий вывод

Модуль `purchaseorder` - это **copy-paste из customerorder** с **критическими ошибками в docstrings**. Код работает правильно и даже имеет валидацию meta.href (чего нет в customerorder), но некорректные docstrings и 100% дублирование кода говорят о необходимости рефакторинга.

**Оценка качества**: 7.0/10 (выше чем paymentout благодаря валидации и использованию domain методов в API)

**Сильные стороны**:
- Отличное переиспользование (88%)
- Domain методы используются в API
- Валидация meta.href присутствует
- Два полезных REST endpoints
- Работает корректно

**Критические проблемы**:
- 🚨 6 некорректных docstrings (copy-paste!)
- 100% дублирование _to_entity с customerorder
- 100% дублирование /search/for-payment endpoint
- Неиспользуемый код (PurchaseOrderFilter)
- Отсутствие явного различия purchase/customer

**Точки роста**:
- Исправить copy-paste ошибки в docstrings
- Вынести дублирующийся код в base
- Удалить неиспользуемый код
- Добавить явное различие типов заказов
- Добавить unit тесты

## 💡 Дополнительные наблюдения

### Copy-paste: история повторяется
```
╔═══════════════════════════════════════════════════════════════════╗
║    PURCHASEORDER vs PAYMENTOUT: ОДИНАКОВАЯ ИСТОРИЯ                ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  Оба модуля:                                                      ║
║  • Скопированы из противоположных модулей                         ║
║  • Имеют 6 некорректных docstrings                                ║
║  • 100% дублирование _to_entity                                   ║
║  • Неиспользуемый Filter класс                                    ║
║  • Бессмысленные алиасы исключений                                ║
║                                                                   ║
║  purchaseorder скопирован из customerorder                        ║
║  paymentout скопирован из paymentin                               ║
║                                                                   ║
║  УРОК: Необходим checklist для copy-paste!                        ║
║                                                                   ║
║  ☐ Все docstrings обновлены?                                      ║
║  ☐ Все комментарии обновлены?                                     ║
║  ☐ Названия классов корректны?                                    ║
║  ☐ Семантика правильная?                                          ║
║  ☐ Тесты обновлены?                                               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

### DRY нарушен трижды
```
┌───────────────────────────────────────────────────────────────┐
│         ДУБЛИРОВАНИЕ МЕЖДУ ЧЕТЫРЬМЯ МОДУЛЯМИ                  │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  _to_entity дублируется:                                      │
│  • paymentin    ~50 строк                                     │
│  • paymentout   ~50 строк  (идентично paymentin)              │
│  • customerorder ~55 строк                                    │
│  • purchaseorder ~55 строк (идентично customerorder)          │
│                                                               │
│  Итого: ~210 строк дублирующегося кода!                       │
│                                                               │
│  /search/for-payment дублируется:                             │
│  • customerorder ~25 строк                                    │
│  • purchaseorder ~25 строк (идентично)                        │
│                                                               │
│  Итого: ~50 строк дублирующегося кода!                        │
│                                                               │
│  ВСЕГО ДУБЛИРОВАНИЯ: ~260 строк кода!                         │
│                                                               │
│  РЕШЕНИЕ:                                                     │
│  1. Вынести _to_entity в базовые классы                       │
│  2. Вынести /search/for-payment в utils                       │
│  3. Экономия: ~250 строк кода                                 │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Положительный момент: валидация
```
╔═══════════════════════════════════════════════════════════════════╗
║        PURCHASEORDER ЛУЧШЕ CUSTOMERORDER В ОДНОМ АСПЕКТЕ          ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  purchaseorder имеет валидацию:                                   ║
║  if not data.get("meta", {}).get("href"):                         ║
║      raise PurchaseOrderNotFoundError(...)                        ║
║  ✓ Хорошо!                                                        ║
║                                                                   ║
║  customerorder НЕ имеет такой валидации                           ║
║  ✗ Плохо!                                                         ║
║                                                                   ║
║  Это показывает что модули создавались независимо                 ║
║  и purchaseorder был улучшен после customerorder                  ║
║                                                                   ║
║  РЕШЕНИЕ:                                                         ║
║  Добавить эту валидацию в BaseDocumentService                     ║
║  чтобы все модули имели её автоматически                          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Семантика purchase vs customer
```
╔═══════════════════════════════════════════════════════════════════╗
║     PURCHASEORDER vs CUSTOMERORDER: СЕМАНТИКА                     ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  В КОДЕ:                                                          ║
║  • entity_type = "purchaseorder" vs "customerorder"               ║
║  • PurchaseOrderEntity vs CustomerOrderEntity (просто имена)      ║
║  • Остальной код: 100% идентичен                                  ║
║                                                                   ║
║  В СЕМАНТИКЕ:                                                     ║
║  • agent_id = поставщик vs покупатель                             ║
║  • Направление: мы покупаем vs у нас покупают                     ║
║  • Оплата: paymentout vs paymentin                                ║
║  • Отгрузка: supply (приемка) vs demand (отгрузка)                ║
║  • Бухгалтерия: расход vs доход                                   ║
║                                                                   ║
║  ПРОБЛЕМА:                                                        ║
║  Семантическое различие НЕ отражено в коде!                       ║
║                                                                   ║
║  РЕШЕНИЕ:                                                         ║
║  Добавить явное различие через:                                   ║
║  • order_type: Literal["purchase", "customer"]                    ║
║  • is_purchase_order/is_customer_order свойства                   ║
║  • Разные __str__ представления                                   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## 🏆 Финальный вердикт

Модуль `purchaseorder` - это **точная копия customerorder** с **критическими copy-paste ошибками** в docstrings. Функционально код работает правильно и даже немного лучше customerorder благодаря валидации meta.href, но дублирование и некорректные docstrings требуют исправления.

**Главные проблемы**:
1. 🚨 6 некорректных docstrings (КРИТИЧНО!)
2. 100% дублирование _to_entity с customerorder (~55 строк)
3. 100% дублирование /search/for-payment (~25 строк)
4. Неиспользуемый код (PurchaseOrderFilter ~40 строк)
5. Отсутствие явного различия purchase/customer

**Положительные моменты**:
- Валидация meta.href (лучше чем customerorder!)
- Domain методы используются в API
- Правильная архитектура
- Работает корректно

**Рекомендация**: 
1. **Срочно** исправить docstrings
2. Вынести общий код в payable_document_base
3. Удалить неиспользуемый код
4. Добавить явное различие purchase/customer
5. Добавить unit тесты

После этих улучшений оценка может вырасти до 8.5/10.

**Оценка**: 7.0/10 - функционально работает хорошо, но много технического долга.

**Главный урок**: Copy-paste без checklist приводит к систематическим ошибкам! Необходим автоматизированный контроль качества (linters, code review).


# PS
```
╔═══════════════════════════════════════════════════════════════════╗
║     PURCHASEORDER vs CUSTOMERORDER - ПОЧЕМУ ОБА НУЖНЫ?            ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  КОД ИДЕНТИЧЕН, НО СЕМАНТИКА ПРОТИВОПОЛОЖНА!                      ║
║                                                                   ║
║  ┌──────────────────────────────────────────────────────────┐     ║
║  │  PURCHASEORDER - Заказ поставщику (ЗАКУПКА)              │     ║
║  ├──────────────────────────────────────────────────────────┤     ║
║  │  • МЫ покупаем товары У поставщика                       │     ║
║  │  • agent_id = поставщик (у кого покупаем)                │     ║
║  │  • organization_id = мы (кто покупает)                   │     ║
║  │  • Оплата: paymentout (МЫ платим поставщику)             │     ║
║  │  • Получение: supply (МЫ получаем товар)                 │     ║
║  │  • Счета: invoicein (поставщик выставляет НАМ)           │     ║
║  │  • Бухгалтерия: РАСХОД                                   │     ║
║  │                                                          │     ║
║  │  Пример: Заказали у "ООО Ромашка" товар на 100000₽       │     ║
║  └──────────────────────────────────────────────────────────┘     ║
║                                                                   ║
║  ┌──────────────────────────────────────────────────────────┐     ║
║  │  CUSTOMERORDER - Заказ покупателя (ПРОДАЖА)              │     ║
║  ├──────────────────────────────────────────────────────────┤     ║
║  │  • Покупатель покупает У НАС                             │     ║
║  │  • agent_id = покупатель (кто покупает)                  │     ║
║  │  • organization_id = мы (кто продает)                    │     ║
║  │  • Оплата: paymentin (покупатель платит НАМ)             │     ║
║  │  • Отгрузка: demand (МЫ отгружаем товар)                 │     ║
║  │  • Счета: invoiceout (МЫ выставляем покупателю)          │     ║
║  │  • Бухгалтерия: ДОХОД                                    │     ║
║  │                                                          │     ║
║  │  Пример: "ООО Василек" заказал у нас товар на 50000₽     │     ║
║  └──────────────────────────────────────────────────────────┘     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Аналогия с платежами

Это **точно такая же ситуация** как с платежами:
```
┌───────────────────────────────────────────────────────────┐
│  paymentin (входящий)      vs    paymentout (исходящий)   │
├───────────────────────────────────────────────────────────┤
│  • ОТ покупателя К нам      │  • ОТ нас К поставщику      │
│  • Код 100% идентичен       │  • Код 100% идентичен       │
│  • НО семантика разная!     │  • НО семантика разная!     │
│  • Один удалить нельзя!     │  • Один удалить нельзя!     │
└───────────────────────────────────────────────────────────┘

Так же и с заказами:

┌───────────────────────────────────────────────────────────┐
│  customerorder (продажа)   vs   purchaseorder (закупка)   │
├───────────────────────────────────────────────────────────┤
│  • Покупатель → нам         │  • Мы → поставщику          │
│  • Код 100% идентичен       │  • Код 100% идентичен       │
│  • НО семантика разная!     │  • НО семантика разная!     │
│  • Один удалить нельзя!     │  • Один удалить нельзя!     │
└───────────────────────────────────────────────────────────┘
```

## Почему код идентичен?
```
╔═══════════════════════════════════════════════════════════════════╗
║            ПОЧЕМУ КОД ОДИНАКОВЫЙ, А МОДУЛИ РАЗНЫЕ?                ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  1. СТРУКТУРА ДАННЫХ ОДИНАКОВА                                    ║
║     И purchaseorder, и customerorder в МойСклад имеют:            ║
║     • id, name, sum, payedSum, shippedSum                         ║
║     • agent, organization, moment                                 ║
║     • project, salesChannel, state                                ║
║                                                                   ║
║  2. API ОДИНАКОВЫЙ                                                ║
║     МойСклад использует одинаковые endpoints:                     ║
║     • GET /entity/purchaseorder/{id}                              ║
║     • GET /entity/customerorder/{id}                              ║
║     • Разница только в entity_type!                               ║
║                                                                   ║
║  3. ЛОГИКА ОБРАБОТКИ ОДИНАКОВА                                    ║
║     • Поиск непогашенных заказов                                  ║
║     • Привязка к платежам                                         ║
║     • Расчет unpaid_amount                                        ║
║     • Проверка is_fully_paid()                                    ║
║                                                                   ║
║  4. РАЗЛИЧИЕ ТОЛЬКО В НАПРАВЛЕНИИ                                 ║
║     Это не код, это БИЗНЕС-ЛОГИКА и СЕМАНТИКА                     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝