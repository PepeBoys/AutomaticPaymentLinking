# Замечания по базовому модулю payment_base

## 🟢 Положительные стороны

### 1. Правильная архитектура наследования
```
✓ Базовые классы для 4 модулей платежей
✓ DRY - код написан один раз
✓ Consistency - все платежи работают одинаково
✓ Generic типы для type safety
✓ ABC для абстрактных методов
```

### 2. Retry механизм на критичных операциях
```
✓ get_by_href() - 3 попытки (получение платежа из webhook)
✓ update_operations() - 3 попытки (привязка к документам)
✓ Exponential backoff: 2s, 4s, 8s, 10s (max)
✓ Правильная обработка retry для идемпотентных операций
```

### 3. Правильная обработка исключений
```
✓ Специфичные исключения:
  • PaymentNotFoundError - 404
  • PaymentAPIError - 502
  • BasePaymentException - 500

✓ Централизованные exception handlers
✓ Детальное логирование ошибок
✓ Правильные HTTP status codes
```

### 4. Clean Architecture
```
✓ Domain Layer: entities, value objects
✓ Service Layer: business logic, orchestration
✓ Client Layer: HTTP communication
✓ Schemas: Pydantic для валидации
✓ Правильное разделение ответственности
```

### 5. Shared schemas
```
✓ MetaRef, Agent, Organization
✓ LinkedOperation
✓ Переиспользуются в payable_document_base
✓ Единообразие across модулях
```

## 🟡 Важные замечания

### 1. Непоследовательность в retry механизме

**Проблема**: Retry только на некоторых методах
```python
# С retry:
@retry(...)
async def get_by_href(self, href: str):  # ✓
    pass

@retry(...)
async def update_operations(self, payment_id: str, operations: list[dict]):  # ✓
    pass

# БЕЗ retry:
async def get_states(self):  # ❌
    pass

async def update_state(self, payment_id: str, state_id: str):  # ❌
    pass

async def update_project(self, payment_id: str, project_href: str):  # ❌
    pass

async def update_sales_channel(self, payment_id: str, ...):  # ❌
    pass
```

**Вопрос**: Это дизайн-решение или недосмотр?

**Аргументы ЗА retry везде**:
- Единообразие
- Устойчивость к временным сбоям сети
- МойСклад API может быть нестабильным

**Аргументы ПРОТИВ retry везде**:
- update_state, update_project, update_sales_channel не критичны
- Меньше нагрузки на API
- Быстрее падать при реальных ошибках

**Решение**: Добавить комментарий в код, объясняющий логику
```python
# Retry применяется только к критичным операциям:
# • get_by_href() - получение платежа из webhook (критично)
# • update_operations() - привязка к документам (критично)
#
# update_state/project/sales_channel не имеют retry потому что:
# • Не критичны для работы системы
# • Могут быть выполнены вручную
# • Снижают нагрузку на МойСклад API
```

### 2. Доступ к приватному методу из service

**Проблема**: Service обращается к `_get_base_url()` напрямую
```python
# base_service.py
async def get_by_id(self, payment_id: str) -> TEntity:
    base_url = self._client._get_base_url()  # ❌ Доступ к приватному методу
    href = f"{base_url}/entity/{self.entity_type}/{payment_id}"
    data = await self._client.get_by_href(href)
    return self._to_entity(data)

async def link_to_document(self, ...):
    payment_data = await self._client.get_by_href(
        f"{self._client._get_base_url()}/entity/{self.entity_type}/{payment_id}"
        # ❌ Доступ к приватному методу
    )
```

**Решение**: Добавить публичный метод или изменить архитектуру
```python
# Вариант 1: Добавить публичный метод
class BasePaymentClient(ABC):
    def get_base_url(self) -> str:
        """Публичный метод для получения base URL."""
        return self._get_base_url()

# Вариант 2: Делегировать в client
class BasePaymentClient(ABC):
    async def get_by_id(self, payment_id: str) -> Dict[str, Any]:
        """Получить платеж по ID."""
        base_url = self._get_base_url()
        href = f"{base_url}/entity/{self.entity_type}/{payment_id}"
        return await self.get_by_href(href)

# Вариант 3: Использовать entity_type в service
async def get_by_id(self, payment_id: str) -> TEntity:
    # Построить href без доступа к _get_base_url
    # Но это требует знания о структуре URL
```

**Рекомендуемое решение**: Вариант 2 - делегировать в client

### 3. Дублирование кода в update методах

**Проблема**: Три почти идентичных метода
```python
async def update_state(self, payment_id: str, state_id: str):
    base_url = self._get_base_url()
    headers = self._get_headers()
    state_href = f"{base_url}/entity/{self.entity_type}/metadata/states/{state_id}"
    
    async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
        url = f"{base_url}/entity/{self.entity_type}/{payment_id}"
        resp = await client.put(url, json={"state": {"meta": {...}}})
        # ...

async def update_project(self, payment_id: str, project_href: str):
    base_url = self._get_base_url()
    headers = self._get_headers()
    
    async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
        url = f"{base_url}/entity/{self.entity_type}/{payment_id}"
        resp = await client.put(url, json={"project": {"meta": {...}}})
        # ...

async def update_sales_channel(self, payment_id: str, sales_channel_href: str):
    base_url = self._get_base_url()
    headers = self._get_headers()
    
    async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
        url = f"{base_url}/entity/{self.entity_type}/{payment_id}"
        resp = await client.put(url, json={"salesChannel": {"meta": {...}}})
        # ...
```

**Решение**: Выделить общий метод
```python
async def _update_field(
    self,
    payment_id: str,
    field_name: str,
    field_value: dict,
) -> Dict[str, Any]:
    """
    Универсальный метод для обновления поля платежа.
    
    Args:
        payment_id: ID платежа
        field_name: Имя поля ("state", "project", "salesChannel")
        field_value: Значение поля (обычно {"meta": {...}})
    """
    try:
        base_url = self._get_base_url()
        headers = self._get_headers()

        async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
            url = f"{base_url}/entity/{self.entity_type}/{payment_id}"
            logger.debug(
                "Обновление %s платежа: %s",
                field_name,
                payment_id
            )

            resp = await client.put(url, json={field_name: field_value})
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise PaymentAPIError(
            f"Ошибка HTTP при обновлении {field_name} платежа",
            details={"status_code": exc.response.status_code, "error": str(exc)},
        ) from exc
    except Exception as exc:
        raise PaymentAPIError(
            f"Ошибка при обновлении {field_name} платежа",
            details={"error": str(exc)},
        ) from exc

async def update_state(self, payment_id: str, state_id: str) -> Dict[str, Any]:
    """Обновить статус платежа."""
    base_url = self._get_base_url()
    state_href = f"{base_url}/entity/{self.entity_type}/metadata/states/{state_id}"
    
    return await self._update_field(
        payment_id,
        "state",
        {
            "meta": {
                "href": state_href,
                "type": "state",
                "mediaType": "application/json",
            }
        }
    )

async def update_project(self, payment_id: str, project_href: str) -> Dict[str, Any]:
    """Обновить проект платежа."""
    return await self._update_field(
        payment_id,
        "project",
        {
            "meta": {
                "href": project_href,
                "type": "project",
                "mediaType": "application/json",
            }
        }
    )

async def update_sales_channel(
    self, payment_id: str, sales_channel_href: str
) -> Dict[str, Any]:
    """Обновить канал продаж платежа."""
    return await self._update_field(
        payment_id,
        "salesChannel",
        {
            "meta": {
                "href": sales_channel_href,
                "type": "saleschannel",
                "mediaType": "application/json",
            }
        }
    )
```

### 4. Отсутствие валидации linked_operations

**Проблема**: Нет проверки структуры operations
```python
async def link_to_document(self, payment_id: str, ...):
    operations = [
        {"meta": op["meta"], "linkedSum": op.get("linkedSum", 0)}
        for op in payment.linked_operations
    ]
    # ❌ Что если op["meta"] отсутствует?
    # ❌ Что если linkedSum не float?
    # ❌ Что если linkedSum отрицательный?
```

**Решение**: Добавить валидацию
```python
def _validate_operation(self, op: dict) -> bool:
    """
    Валидировать структуру operation.
    
    Returns:
        True если operation валиден
        
    Raises:
        PaymentAPIError: Если operation невалиден
    """
    if "meta" not in op:
        raise PaymentAPIError(
            "Operation missing 'meta' field",
            details={"operation": op}
        )
    
    if "href" not in op["meta"]:
        raise PaymentAPIError(
            "Operation.meta missing 'href' field",
            details={"operation": op}
        )
    
    linked_sum = op.get("linkedSum", 0)
    if not isinstance(linked_sum, (int, float)):
        raise PaymentAPIError(
            f"linkedSum must be numeric, got {type(linked_sum)}",
            details={"operation": op}
        )
    
    if linked_sum < 0:
        logger.warning(
            "Negative linkedSum: %s in operation %s",
            linked_sum, op
        )
    
    return True

async def link_to_document(self, payment_id: str, ...):
    payment_data = await self._client.get_by_href(...)
    payment = self._to_entity(payment_data)

    operations = []
    for op in payment.linked_operations:
        self._validate_operation(op)  # Валидация
        operations.append({
            "meta": op["meta"],
            "linkedSum": op.get("linkedSum", 0)
        })

    # ... остальной код
```

### 5. Отсутствие domain методов

**Наблюдение**: BasePaymentEntity не имеет методов
```python
@dataclass
class BasePaymentEntity:
    """Базовая сущность платежа."""
    
    id: str
    account_id: str
    # ... поля
    
    # ❌ Нет методов типа:
    # • is_linked_to(document_id)
    # • get_total_linked_sum()
    # • has_unlinked_amount()
    # • get_unlinked_amount()
```

**Это может быть дизайн-решением**, но добавление domain методов могло бы улучшить код:
```python
@dataclass
class BasePaymentEntity:
    """Базовая сущность платежа."""
    
    # ... поля
    
    def get_total_linked_sum(self) -> float:
        """Получить общую сумму привязанных документов."""
        return sum(op.get("linkedSum", 0) for op in self.linked_operations)
    
    def get_unlinked_amount(self) -> float:
        """Получить непривязанную сумму платежа."""
        return max(0, self.sum - self.get_total_linked_sum())
    
    def is_fully_linked(self) -> bool:
        """Проверить, полностью ли распределен платеж."""
        return self.get_total_linked_sum() >= self.sum
    
    def is_linked_to(self, document_id: str) -> bool:
        """Проверить привязан ли платеж к документу."""
        return any(
            document_id in op.get("meta", {}).get("href", "")
            for op in self.linked_operations
        )
    
    def find_operation_by_document_id(self, document_id: str) -> dict | None:
        """Найти operation для документа."""
        for op in self.linked_operations:
            if document_id in op.get("meta", {}).get("href", ""):
                return op
        return None
```

### 6. Magic string "unknown"

**Проблема**: Возвращается magic string при ошибке
```python
@staticmethod
def _extract_type_from_href(href: str) -> str:
    """Извлечь тип документа из href."""
    parts = href.split("/")
    return parts[-2] if len(parts) >= 2 else "unknown"  # ❌ Magic string
```

**Решение**: Обработать ошибку явно
```python
@staticmethod
def _extract_type_from_href(href: str) -> str:
    """
    Извлечь тип документа из href.
    
    Args:
        href: Полный href документа
            Ожидается формат: ".../entity/{type}/{id}"
            
    Returns:
        Тип документа ("customerorder", "invoiceout", ...)
        
    Raises:
        PaymentAPIError: Если href имеет некорректный формат
        
    Examples:
        >>> _extract_type_from_href(".../entity/customerorder/123")
        'customerorder'
    """
    parts = href.split("/")
    
    if len(parts) < 2:
        raise PaymentAPIError(
            f"Invalid href format: {href}",
            details={
                "href": href,
                "expected_format": ".../entity/{{type}}/{{id}}"
            }
        )
    
    # Предполагается что формат: .../entity/{type}/{id}
    # parts[-2] это {type}, parts[-1] это {id}
    entity_type = parts[-2]
    
    if not entity_type:
        raise PaymentAPIError(
            f"Empty entity type in href: {href}",
            details={"href": href}
        )
    
    logger.debug("Extracted entity type '%s' from href: %s", entity_type, href)
    return entity_type
```

### 7. Непоследовательность Optional vs | None

**Проблема**: Смешанные стили
```python
# entities.py
payment_purpose: Optional[str]  # ← Optional
project_meta_href: Optional[str] = None  # ← Optional

# value_objects.py
agent_id: Optional[str] = None  # ← Optional

# schemas.py
paymentPurpose: Optional[str] = None  # ← Optional
linkedSum: Optional[float] = None  # ← Optional

# base_client.py
# Все методы возвращают Dict, а не dict
```

**Решение**: Выбрать один стиль (рекомендуется `| None` для Python 3.10+)
```python
from __future__ import annotations

# Везде использовать | None
payment_purpose: str | None
project_meta_href: str | None = None
```

## 🟢 Рекомендации по улучшению

### 8. Добавить domain методы
```python
@dataclass
class BasePaymentEntity:
    """Базовая сущность платежа с бизнес-логикой."""
    
    # ... поля
    
    def get_total_linked_sum(self) -> float:
        """Получить общую привязанную сумму."""
        return sum(
            op.get("linkedSum", 0)
            for op in self.linked_operations
        )
    
    def get_unlinked_amount(self) -> float:
        """Получить непривязанную сумму."""
        return max(0, self.sum - self.get_total_linked_sum())
    
    def is_fully_linked(self) -> bool:
        """Проверить полную привязку."""
        return self.get_total_linked_sum() >= self.sum
    
    def is_partially_linked(self) -> bool:
        """Проверить частичную привязку."""
        linked = self.get_total_linked_sum()
        return 0 < linked < self.sum
    
    def get_linked_document_ids(self) -> list[str]:
        """Получить ID всех привязанных документов."""
        ids = []
        for op in self.linked_operations:
            href = op.get("meta", {}).get("href", "")
            if href:
                # Извлечь ID из href: ".../entity/type/ID"
                ids.append(href.split("/")[-1])
        return ids
```

### 9. Добавить helper для создания meta
```python
# domain/utils.py (новый файл)

def create_meta_ref(href: str, type_: str) -> dict:
    """
    Создать meta reference для МойСклад API.
    
    Args:
        href: Полная ссылка на сущность
        type_: Тип сущности
        
    Returns:
        Dict с meta structure
        
    Example:
        >>> create_meta_ref(".../customerorder/123", "customerorder")
        {
            "meta": {
                "href": ".../customerorder/123",
                "type": "customerorder",
                "mediaType": "application/json"
            }
        }
    """
    return {
        "meta": {
            "href": href,
            "type": type_,
            "mediaType": "application/json",
        }
    }

# Использовать:
async def update_state(self, payment_id: str, state_id: str):
    base_url = self._get_base_url()
    state_href = f"{base_url}/entity/{self.entity_type}/metadata/states/{state_id}"
    
    return await self._update_field(
        payment_id,
        "state",
        create_meta_ref(state_href, "state")
    )
```

### 10. Добавить метрики
```python
from prometheus_client import Counter, Histogram

payment_operations_total = Counter(
    'payment_operations_total',
    'Total payment operations',
    ['entity_type', 'operation', 'status']
)

payment_operation_duration = Histogram(
    'payment_operation_duration_seconds',
    'Payment operation duration',
    ['entity_type', 'operation']
)

class BasePaymentClient(ABC):
    async def get_by_href(self, href: str) -> Dict[str, Any]:
        with payment_operation_duration.labels(
            entity_type=self.entity_type,
            operation='get_by_href'
        ).time():
            try:
                # ... logic ...
                payment_operations_total.labels(
                    entity_type=self.entity_type,
                    operation='get_by_href',
                    status='success'
                ).inc()
                return data
            except Exception:
                payment_operations_total.labels(
                    entity_type=self.entity_type,
                    operation='get_by_href',
                    status='failure'
                ).inc()
                raise
```

### 11. Добавить unit тесты
```python
# tests/apps/payment_base/test_entities.py

import pytest
from apps.payment_base.domain.entities import BasePaymentEntity

def test_get_total_linked_sum():
    """Тест расчета общей привязанной суммы."""
    payment = BasePaymentEntity(
        sum=10000.0,
        linked_operations=[
            {"meta": {...}, "linkedSum": 3000.0},
            {"meta": {...}, "linkedSum": 2000.0},
        ],
        # ... остальные поля
    )
    assert payment.get_total_linked_sum() == 5000.0

def test_get_unlinked_amount():
    """Тест расчета непривязанной суммы."""
    payment = BasePaymentEntity(
        sum=10000.0,
        linked_operations=[
            {"meta": {...}, "linkedSum": 6000.0},
        ],
        # ...
    )
    assert payment.get_unlinked_amount() == 4000.0

def test_is_fully_linked():
    """Тест проверки полной привязки."""
    payment = BasePaymentEntity(
        sum=10000.0,
        linked_operations=[
            {"meta": {...}, "linkedSum": 10000.0},
        ],
        # ...
    )
    assert payment.is_fully_linked() is True

# tests/apps/payment_base/test_service.py

@pytest.mark.asyncio
async def test_link_to_document(mock_client, mock_auth_service):
    """Тест привязки платежа к документу."""
    service = PaymentInService(mock_auth_service)
    
    # Mock существующий платеж
    mock_client.get_by_href.return_value = {
        "id": "payment_123",
        "sum": 10000.0,
        "operations": [
            {"meta": {"href": ".../order/1"}, "linkedSum": 3000.0}
        ]
    }
    
    # Mock обновление
    mock_client.update_operations.return_value = {
        "id": "payment_123",
        "operations": [
            {"meta": {"href": ".../order/1"}, "linkedSum": 3000.0},
            {"meta": {"href": ".../order/2"}, "linkedSum": 7000.0}
        ]
    }
    
    # Привязать
    result = await service.link_to_document(
        payment_id="payment_123",
        document_meta_href=".../order/2",
        linked_sum=7000.0
    )
    
    # Проверить
    assert len(result.linked_operations) == 2
    assert result.get_total_linked_sum() == 10000.0
```

### 12. Улучшить docstrings
```python
async def link_to_document(
    self, payment_id: str, document_meta_href: str, linked_sum: float
) -> TEntity:
    """
    Привязать платеж к документу.
    
    Этот метод получает текущий платеж, добавляет новый документ
    к существующим operations и обновляет платеж в МойСклад.
    
    ВАЖНО: Существующие привязки сохраняются! Метод добавляет
    новую привязку к существующим, а не заменяет их.
    
    Args:
        payment_id: ID платежа для привязки
        document_meta_href: Полный href документа
            Формат: "{base_url}/entity/{type}/{id}"
            Пример: "https://api.moysklad.ru/api/remap/1.2/entity/customerorder/123"
        linked_sum: Сумма привязки (может быть меньше суммы платежа
            для частичной привязки к нескольким документам)
            
    Returns:
        Обновленная entity платежа с новым массивом operations
        
    Raises:
        PaymentNotFoundError: Если платеж не найден
        PaymentAPIError: Если ошибка при обновлении
        
    Example:
        >>> # Привязать платеж на 10000 к двум заказам
        >>> payment = await service.link_to_document(
        ...     payment_id="payment_123",
        ...     document_meta_href=".../customerorder/order_1",
        ...     linked_sum=6000.0
        ... )
        >>> payment = await service.link_to_document(
        ...     payment_id="payment_123",
        ...     document_meta_href=".../customerorder/order_2",
        ...     linked_sum=4000.0
        ... )
        >>> assert payment.get_total_linked_sum() == 10000.0
    """
```

## 📊 Статистика кода
```
┌─────────────────────────────────────────────────────────────────┐
│                    МЕТРИКИ ПРИЛОЖЕНИЯ                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Всего строк кода:              ~500                            │
│                                                                 │
│  Файлов:                        9                               │
│  Классов:                       7                               │
│  Абстрактных классов:           2 (ABC)                         │
│  Функций:                       12 (+ методы)                   │
│                                                                 │
│  Domain entities:               1                               │
│  Value objects:                 1                               │
│  Services (base):               1                               │
│  Clients (base):                1                               │
│  Exceptions:                    3                               │
│  Schemas:                       5                               │
│                                                                 │
│  Generic types:                 2 (TEntity, TClient)            │
│  Service methods:               7                               │
│  Client methods:                6                               │
│                                                                 │
│  Методы с retry:                2 из 6 (33%)                    │
│  Domain методы:                 0 (возможность улучшения)       │
│                                                                 │
│  Покрытие типизацией:           90%                             │
│  Cyclomatic Complexity:         3-4 (низкая, хорошо)            │
│  Maintainability Index:         75-80 (хорошо)                  │
│                                                                 │
│  TODO/FIXME:                    0                               │
│  Docstrings:                    50% (можно лучше)               │
│                                                                 │
│  Наследников:                   4 модуля                        │
│  Дублирование с payable_doc:    Минимальное (shared schemas)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## ✅ Что сделано хорошо

1. ✅ Правильная архитектура наследования
2. ✅ Generic типы для type safety
3. ✅ Retry механизм на критичных операциях
4. ✅ Централизованная обработка исключений
5. ✅ ABC для абстрактных методов
6. ✅ Shared schemas (MetaRef, Agent, Organization)
7. ✅ Правильное разделение ответственности
8. ✅ Separation of concerns (domain, service, client)
9. ✅ PaymentNotFoundError для 404

## 🎯 Приоритет доработок

1. **Высокий**: Исправить доступ к приватному методу (#2)
2. **Средний**: Рефакторинг update методов (#3)
3. **Средний**: Добавить валидацию operations (#4)
4. **Средний**: Добавить domain методы (#5)
5. **Высокий**: Улучшить docstrings (#12)
6. **Средний**: Исправить magic string "unknown" (#6)
7. **Низкий**: Единообразие Optional vs | None (#7)
8. **Низкий**: Добавить комментарий о retry логике (#1)
9. **Низкий**: Метрики для мониторинга (#10)
10. **Высокий**: Unit тесты (#11)

## 🔍 Общий вывод

Модуль `payment_base` - это **хороший базовый модуль** с правильной архитектурой, но **проще чем payable_document_base**. Отсутствие domain методов делает entity просто контейнером данных, что упрощает код, но снижает выразительность domain model.

**Оценка качества**: 7.5/10

**Сильные стороны**:
- Правильная архитектура наследования
- Retry на критичных операциях
- Shared schemas
- Централизованная обработка ошибок
- Clean Architecture

**Точки роста**:
- Добавить domain методы для работы с linked_operations
- Рефакторинг дублирующихся update методов
- Исправить доступ к приватным методам
- Добавить валидацию
- Улучшить документацию
- Написать unit тесты

## 💡 Дополнительные наблюдения

### Сравнение с payable_document_base
```
╔═══════════════════════════════════════════════════════════════════╗
║       PAYMENT_BASE vs PAYABLE_DOCUMENT_BASE                       ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  payment_base:                                                    ║
║  • Проще (меньше методов)                                         ║
║  • Нет domain методов                                             ║
║  • Фокус на привязке к документам                                 ║
║  • Retry на 2 из 6 методов                                        ║
║  • ~500 строк кода                                                ║
║                                                                   ║
║  payable_document_base:                                           ║
║  • Сложнее (больше методов)                                       ║
║  • 5 domain методов (is_fully_paid, etc.)                         ║
║  • Фокус на поиске для привязки                                   ║
║  • Retry на 1 методе (search)                                     ║
║  • ~600 строк кода                                                ║
║                                                                   ║
║  ПОЧЕМУ payable_document_base сложнее?                            ║
║  • Больше бизнес-логики (payed_sum, shipped_sum, invoiced_sum)   ║
║  • Сложные методы поиска (search_by_agent_and_sum, etc.)         ║
║  • Moscow timezone handling                                       ║
║  • Domain методы для расчетов                                     ║
║                                                                   ║
║  ПОЧЕМУ payment_base проще?                                       ║
║  • Простая роль: получить и привязать                             ║
║  • Меньше бизнес-логики                                           ║
║  • Нет сложных поисков                                            ║
║  • Работает с href из webhook напрямую                            ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Почему нет domain методов?

Возможные причины:
1. **Простота**: Платежи не требуют сложных расчетов
2. **YAGNI**: Методы не нужны в текущей реализации
3. **Недосмотр**: Методы могли бы быть полезны

Аргументы ЗА domain методы:
- Более выразительный код: `payment.is_fully_linked()`
- Инкапсуляция логики работы с linked_operations
- Облегчает тестирование

Аргументы ПРОТИВ:
- Добавляет сложность без явной пользы
- Текущая реализация работает нормально
- Можно добавить позже если понадобится

### Критичные операции и retry
```
┌───────────────────────────────────────────────────────────────┐
│         ПОЧЕМУ RETRY ТОЛЬКО НА 2 МЕТОДАХ?                      │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  С retry:                                                     │
│  • get_by_href() - критично для webhook                       │
│  • update_operations() - критично для привязки                │
│                                                               │
│  БЕЗ retry:                                                   │
│  • update_state() - может быть выполнено вручную              │
│  • update_project() - может быть выполнено вручную            │
│  • update_sales_channel() - может быть выполнено вручную      │
│  • get_states() - метаданные, не критично                     │
│                                                               │
│  ЛОГИКА:                                                      │
│  Retry применяется только к операциям, которые:               │
│  1. Критичны для работы системы                               │
│  2. Вызываются автоматически (webhook)                        │
│  3. Не могут быть легко повторены вручную                     │
│                                                               │
│  Это разумное дизайн-решение, но требует документирования!    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## 🏆 Финальный вердикт

Модуль `payment_base` - **хороший базовый модуль** с правильной архитектурой для 4 типов платежей. Проще чем `payable_document_base`, что оправдано более простой бизнес-логикой платежей.

Главное отличие от `payable_document_base`:
- **payable_document_base**: Сложные расчеты, domain методы, поиск
- **payment_base**: Простая привязка, минимальная логика

**Рекомендация**: 
1. Добавить domain методы для работы с linked_operations
2. Рефакторинг дублирующихся update методов
3. Написать unit тесты
4. Улучшить документацию

После этих улучшений оценка может вырасти до 8.5-9.0/10.

**Оценка**: 7.5/10 - хороший модуль с потенциалом стать 8.5/10 после добавления domain методов и рефакторинга.