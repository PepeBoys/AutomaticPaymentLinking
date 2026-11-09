# Приложение vendor_api - Интеграция с МойСклад Vendor API

## Описание

Модуль `vendor_api` реализует серверную часть Vendor API для интеграции приложения с МойСклад как официального решения (vendor application). Это **standalone модуль**, не наследующий от базовых классов payment/document, а реализующий полный цикл работы с Vendor API МойСклад.

**Ключевое назначение**: Обработка lifecycle событий приложения (активация, деактивация) и управление вебхуками при установке/удалении приложения в аккаунтах МойСклад.

**ВАЖНО**: Vendor API - это способ интеграции приложений с МойСклад на уровне "маркетплейса", где приложение устанавливается через интерфейс МойСклад.

## Архитектура
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VENDOR API LAYER (REST)                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  api.py - МойСклад Vendor API Endpoints                            │     │
│  │  • PUT    /{app_id}/{account_id}        → Активация приложения     │     │
│  │  • DELETE /{app_id}/{account_id}        → Деактивация приложения   │     │
│  │  • PUT    /{app_id}/{account_id}/event  → Получение событий        │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY LAYER                                      │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  security.py - JWT Verification & Signing                          │     │
│  │  • verify_vendor_jwt(token)  → Проверка подписи HS256              │     │
│  │  • sign_vendor_jwt(claims)   → Подпись для исходящих запросов      │     │
│  │  • Replay attack protection  → JTI tracking                        │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SERVICE LAYER                                       │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  VendorApiService                                                  │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  Lifecycle управление:                                             │     │
│  │  • activate_app()    → Активация приложения                        │     │
│  │  • deactivate_app()  → Деактивация приложения                      │     │
│  │                                                                    │     │
│  │  Безопасность:                                                     │     │
│  │  • _validate_app_id()   → Проверка app_id                          │     │
│  │  • _validate_app_uid()  → Проверка app_uid                         │     │
│  │  • _verify_jwt()        → Проверка JWT подписи                     │     │
│  │  • _guard_replay()      → Защита от replay attacks                 │     │
│  │                                                                    │     │
│  │  Интеграция с вебхуками:                                           │     │
│  │  • cleanup_account_webhooks()  → Очистка при переустановке         │     │
│  │  • Управление через WebhookService                                 │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REPOSITORY LAYER                                    │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  VendorAccountRepository                                           │     │
│  │  • get_by_account_id()     → Получить аккаунт                      │     │
│  │  • upsert_account()        → Создать/обновить аккаунт              │     │
│  │  • deactivate_account()    → Деактивировать аккаунт                │     │
│  │  • list_active_accounts()  → Список активных аккаунтов             │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  VendorJtiRepository                                               │     │
│  │  • is_used()          → Проверить использован ли JTI               │     │
│  │  • save()             → Сохранить JTI                              │     │
│  │  • cleanup_expired()  → Очистка истекших JTI                       │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE LAYER                                      │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  VendorAccount - Информация об установках                          │    │
│  │  • account_id     - ID аккаунта МойСклад                           │    │
│  │  • access_token   - OAuth токен для API                            │    │
│  │  • base_url       - URL API для аккаунта                           │    │
│  │  • app_uid        - UID приложения                                 │    │
│  │  • is_active      - Статус активации                               │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  VendorJwtJti - Защита от replay attacks                           │    │
│  │  • jti          - Уникальный идентификатор JWT                     │    │
│  │  • expires_at   - Время истечения                                  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════╗
║                         SCHEMAS (Pydantic)                                 ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ActivationPayload         - Payload активации от МойСклад                 ║
║  ActivationResponse        - Ответ на активацию                            ║
║  VendorEventPayload        - Payload событий от МойСклад                   ║
║  AccessItem                - Элемент доступа с токеном                     ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

## Жизненный цикл приложения
```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LIFECYCLE VENDOR APPLICATION                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. УСТАНОВКА (через МойСклад UI)                                       │
│     Пользователь: Маркетплейс → Найти приложение → Установить           │
│     ↓                                                                   │
│                                                                         │
│  2. АКТИВАЦИЯ (МойСклад → Наш сервер)                                   │
│     PUT /vendor/1.0/apps/{app_id}/{account_id}                          │
│     ┌─────────────────────────────────────────────────────┐             │
│     │ Payload:                                            │             │
│     │ {                                                   │             │
│     │   "appUid": "...",                                  │             │
│     │   "accountName": "ООО Рога и Копыта",               │             │
│     │   "access": [{                                      │             │
│     │     "resource": "https://api.moysklad.ru/...",      │             │
│     │     "access_token": "oauth_token_here"              │             │
│     │   }]                                                │             │
│     │ }                                                   │             │
│     └─────────────────────────────────────────────────────┘             │
│     ↓                                                                   │
│                                                                         │
│  3. НАША ОБРАБОТКА                                                      │
│     ✓ Проверка JWT подписи (HS256)                                      │
│     ✓ Защита от replay (JTI tracking)                                   │
│     ✓ Сохранение access_token в БД                                      │
│     ✓ Очистка старых вебхуков (если переустановка)                      │
│     ✓ Настройка auth_service с токеном                                  │
│     ✓ return {"status": "Activated"}                                    │
│     ↓                                                                   │
│                                                                         │
│  4. РАБОТА ПРИЛОЖЕНИЯ                                                   │
│     • Пользователь настраивает привязки через UI                        │
│     • Создаются вебхуки в МойСклад                                      │
│     • Обработка платежей и документов                                   │
│     ↓                                                                   │
│                                                                         │
│  5. ДЕАКТИВАЦИЯ (МойСклад → Наш сервер)                                 │
│     DELETE /vendor/1.0/apps/{app_id}/{account_id}                       │
│     ✓ Проверка JWT                                                      │
│     ✓ Защита от replay                                                  │
│     ✓ Удаление записей вебхуков из БД                                   │
│     ✓ Деактивация account (is_active=False)                             │
│     ✓ Очистка access_token                                              │
│                                                                         │
│  ВАЖНО: Токен отзывается МС ДО вызова DELETE!                           │
│  → Нельзя удалить вебхуки через API при деактивации                     │
│  → Вебхуки остаются в МС и переиспользуются при реактивации             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Безопасность

### JWT Verification (HS256)
```
┌────────────────────────────────────────────────────────────────┐
│                    JWT VERIFICATION                            │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  МойСклад подписывает запросы JWT с алгоритмом HS256          │
│  Секретный ключ: ms_vendor_secret_key (из .env)                │
│                                                                │
│  JWT Structure:                                                │
│  header.payload.signature                                      │
│                                                                │
│  header = {                                                    │
│    "alg": "HS256",                                             │
│    "typ": "JWT"                                                │
│  }                                                             │
│                                                                │
│  payload = {                                                   │
│    "iat": 1234567890,  ← Issued at                            │
│    "exp": 1234568190,  ← Expires (5 минут)                    │
│    "jti": "unique-id", ← JWT ID для replay protection         │
│    "sub": "app_uid"    ← Subject (наш app_uid)                │
│  }                                                             │
│                                                                │
│  Проверка:                                                     │
│  1. Парсинг header и payload                                   │
│  2. Вычисление expected_signature = HMAC-SHA256(...)           │
│  3. Сравнение с фактической подписью (timing-safe)             │
│  4. Проверка exp (не истек ли)                                 │
│  5. Проверка required claims (exp, iat, jti)                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Replay Attack Protection
```
┌────────────────────────────────────────────────────────────────┐
│                  REPLAY ATTACK PROTECTION                      │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Проблема: Злоумышленник может перехватить JWT и повторить     │
│           запрос активации/деактивации                         │
│                                                                │
│  Решение: JTI (JWT ID) tracking                                │
│                                                                │
│  1. Каждый JWT содержит уникальный jti                         │
│  2. При получении JWT:                                         │
│     • Очистка истекших JTI из БД                               │
│     • Проверка: использован ли этот jti ранее?                 │
│     • Если ДА → reject (409 Conflict)                          │
│     • Если НЕТ → сохранить jti в БД с expires_at               │
│  3. JTI хранится до истечения токена                           │
│  4. Периодическая очистка истекших JTI                         │
│                                                                │
│  Таблица VendorJwtJti:                                         │
│  ┌──────────────────┬───────────────────────┐                  │
│  │ jti (UNIQUE)     │ expires_at            │                  │
│  ├──────────────────┼───────────────────────┤                  │
│  │ uuid-1234        │ 2024-01-15 10:35:00   │                  │
│  │ uuid-5678        │ 2024-01-15 10:40:00   │                  │
│  └──────────────────┴───────────────────────┘                  │
│                                                                │
│  Защита: Даже если токен украден, его нельзя использовать      │
│          дважды!                                               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Ключевые особенности
```
╔═══════════════════════════════════════════════════════════════════╗
║                    КЛЮЧЕВЫЕ ОСОБЕННОСТИ                           ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  1. VENDOR API INTEGRATION                                        ║
║     • Официальная интеграция через Vendor API МойСклад            ║
║     • Lifecycle управление (activate/deactivate)                  ║
║     • Multi-tenant через account_id                               ║
║                                                                   ║
║  2. БЕЗОПАСНОСТЬ                                                  ║
║     • JWT verification (HS256)                                    ║
║     • Replay attack protection (JTI tracking)                     ║
║     • App ID validation                                           ║
║     • App UID validation                                          ║
║                                                                   ║
║  3. УПРАВЛЕНИЕ ВЕБХУКАМИ                                          ║
║     • Очистка при переустановке (если was_active=False)           ║
║     • Переиспользование при реактивации (если was_active=True)    ║
║     • Невозможность удаления при деактивации (токен отозван)      ║
║                                                                   ║
║  4. ACCESS TOKEN MANAGEMENT                                       ║
║     • Сохранение OAuth токенов в БД                               ║
║     • Автоматическая настройка auth_service                       ║
║     • Per-account base_url support                                ║
║                                                                   ║
║  5. REPOSITORY PATTERN                                            ║
║     • VendorAccountRepository - управление аккаунтами             ║
║     • VendorJtiRepository - JTI tracking                          ║
║     • Proper separation of concerns                               ║
║                                                                   ║
║  6. INTEGRATION WITH WEBHOOK SERVICE                              ║
║     • cleanup_account_webhooks() при активации                    ║
║     • delete_all_by_account_id() при деактивации                  ║
║     • Координация через WebhookService                            ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Примеры использования

### Активация приложения (МойСклад → Сервер)
```python
# МойСклад отправляет:
PUT /moysklad/vendor/1.0/apps/{app_id}/{account_id}
Authorization: Bearer <jwt_token>

{
  "appUid": "our-app-uid",
  "accountName": "ООО Рога и Копыта",
  "access": [{
    "resource": "https://api.moysklad.ru/api/remap/1.2",
    "access_token": "oauth_token_123456",
    "scope": ["admin"]
  }]
}

# Наша обработка:
async def activate_solution(...):
    # 1. Validate app_id/app_uid
    service._validate_app_id(app_id)
    service._validate_app_uid(payload.appUid)
    
    # 2. Verify JWT + replay guard
    claims = service._verify_jwt(jwt_token)
    await service._guard_replay(claims)
    
    # 3. Extract access_token
    access_token, base_url = service._find_access_token_and_base_url(payload)
    
    # 4. Save to DB
    await service._accounts.upsert_account(
        account_id=account_id,
        access_token=access_token,
        base_url=base_url,
        app_uid=settings.ms_app_uid,
    )
    
    # 5. Configure auth
    service._auth_service.set_access_token(
        access_token,
        base_url=base_url,
        account_id=account_id
    )
    
    # 6. Cleanup webhooks (if needed)
    if not was_active:
        cleanup_stats = await service._webhook_service.cleanup_account_webhooks(
            account_id
        )
    
    # 7. Commit
    await session.commit()
    
    return {"status": "Activated"}
```

### Деактивация приложения
```python
# МойСклад отправляет:
DELETE /moysklad/vendor/1.0/apps/{app_id}/{account_id}
Authorization: Bearer <jwt_token>

# Наша обработка:
async def deactivate_solution(...):
    # 1. Verify JWT + replay guard
    claims = service._verify_jwt(jwt_token)
    await service._guard_replay(claims)
    
    # 2. Delete webhooks from DB only
    # (токен уже отозван МС, нельзя удалить через API)
    deleted_count = await service._uow.webhooks.delete_all_by_account_id(
        account_id
    )
    
    # 3. Deactivate account
    await service._accounts.deactivate_account(account_id)
    service._auth_service.clear_access_token()
    
    # 4. Commit
    await session.commit()
    
    return 204 No Content
```

### Получение событий (placeholder)
```python
# МойСклад может отправлять события:
PUT /moysklad/vendor/1.0/apps/{app_id}/{account_id}/event
Authorization: Bearer <jwt_token>

{
  "eventType": "SETTINGS_CHANGED",
  "data": {...},
  "moment": "2024-01-15T10:30:00Z"
}

# Наша обработка:
async def receive_event(...):
    service._validate_app_id(app_id)
    service._verify_jwt(jwt_token)
    
    logger.info("Received vendor event: type=%s", payload.eventType)
    
    # TODO: Implement event handling
    return {"status": "accepted"}
```

## Связанные модули
```
┌─────────────────────────────────────────────────────────────────┐
│                     ЗАВИСИТ ОТ                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ms_auth.MySkladAuthService                                     │
│    └─► set_access_token() - настройка токена                    │
│    └─► clear_access_token() - очистка токена                    │
│    └─► get_base_url() - получение base URL                      │
│                                                                 │
│  hooks.WebhookService                                           │
│    └─► cleanup_account_webhooks() - очистка при активации       │
│                                                                 │
│  hooks.UnitOfWork                                               │
│    └─► webhooks.delete_all_by_account_id() - очистка БД         │
│                                                                 │
│  core.database                                                  │
│    └─► get_session() - сессия БД                                │
│                                                                 │
│  core.config.settings                                           │
│    └─► ms_app_id, ms_app_uid, ms_vendor_secret_key              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     ИСПОЛЬЗУЕТСЯ В                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  main.py                                                        │
│    └─► app.include_router(vendor_api.router)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Проблемы и решения

### Проблема: Токен отзывается перед deactivate
```
╔═══════════════════════════════════════════════════════════════════╗
║         КРИТИЧЕСКАЯ ОСОБЕННОСТЬ VENDOR API                        ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ПРОБЛЕМА:                                                        ║
║  МойСклад ОТЗЫВАЕТ access_token ДО вызова DELETE endpoint         ║
║                                                                   ║
║  Последовательность:                                              ║
║  1. МС: Revoke access_token                                       ║
║  2. МС: DELETE /vendor/.../apps/{app_id}/{account_id}             ║
║  3. Наш код: Попытка удалить вебхуки через API                    ║
║  4. МС API: 401 Unauthorized (токен недействителен!)              ║
║                                                                   ║
║  РЕШЕНИЕ:                                                         ║
║  При деактивации:                                                 ║
║  • Удалять записи вебхуков ТОЛЬКО из нашей БД                     ║
║  • НЕ пытаться удалить через МС API                               ║
║  • Вебхуки остаются в МС                                          ║
║  • При следующей активации вебхуки ПЕРЕИСПОЛЬЗУЮТСЯ               ║
║                                                                   ║
║  ПРЕИМУЩЕСТВО:                                                    ║
║  Быстрая реактивация - вебхуки уже настроены!                     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Проблема: Двойная активация от МС
```
╔═══════════════════════════════════════════════════════════════════╗
║            ДВОЙНАЯ АКТИВАЦИЯ ОТ МОЙСКЛАД                          ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  НАБЛЮДЕНИЕ:                                                      ║
║  МойСклад может отправить ДВА запроса активации подряд            ║
║  с разными JWT токенами                                           ║
║                                                                   ║
║  ПРИЧИНА:                                                         ║
║  Внутренняя логика МойСклад (retry, confirmation, etc.)           ║
║                                                                   ║
║  РЕШЕНИЕ:                                                         ║
║  1. Проверять was_active перед очисткой вебхуков                  ║
║  2. Если account уже активен → пропустить cleanup                 ║
║  3. Если account неактивен → выполнить cleanup                    ║
║                                                                   ║
║  Код:                                                             ║
║  existing_account = await self._accounts.get_by_account_id(...)   ║
║  was_active = existing_account and existing_account.is_active     ║
║                                                                   ║
║  if not was_active:                                               ║
║      await self._webhook_service.cleanup_account_webhooks(...)    ║
║  else:                                                            ║
║      # Пропустить cleanup, переиспользовать вебхуки               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Конфигурация
```ini
# .env
MS_APP_ID=your-app-id-from-moysklad
MS_APP_UID=your-app-uid-from-moysklad
MS_VENDOR_SECRET_KEY=your-secret-key-for-jwt
MS_BASE_URL=https://api.moysklad.ru/api/remap/1.2
```