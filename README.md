# Automatic Payment Linking

Сервис на FastAPI для автоматической привязки платежей в МойСклад. Проект включает
интеграции с API МойСклад, обработку вебхуков и внутренние механизмы сопоставления
документов/платежей.

## Быстрый старт (Docker Compose)

1. Создайте файл `.env` на основе `.env.example`.
2. Убедитесь, что файл базы данных находится в корне проекта:
   ```bash
   touch db.sqlite3
   ```
3. Запустите сервис:
   ```bash
   docker-compose up --build
   ```

Сервис будет доступен по адресу: `http://localhost:8000`.

## Запуск локально (без Docker)

1. Установите зависимости:
   ```bash
   poetry install
   ```
2. Экспортируйте переменные окружения или создайте `.env`.
3. Запустите приложение:
   ```bash
   poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000
   ```

## Переменные окружения (.env)

Все переменные используют префикс `APL_`. Пример доступен в `.env.example`.

### Database
- `APL_DATABASE_URL` — строка подключения SQLAlchemy (SQLite по умолчанию).

### Container (Docker)
- `APL_HOST` — host для Uvicorn.
- `APL_PORT` — port для Uvicorn.

### МойСклад API
- `APL_MS_LOGIN` — логин МойСклад.
- `APL_MS_PASSWORD` — пароль МойСклад.
- `APL_MS_BASE_URL` — базовый URL API МойСклад.

### МойСклад Vendor API
- `APL_MS_APP_ID` — ID приложения.
- `APL_MS_APP_UID` — UID приложения.
- `APL_MS_VENDOR_SECRET_KEY` — секретный ключ.
- `APL_VENDOR_API_ENDPOINT_BASE` — базовый endpoint Vendor API.

### Webhooks
- `APL_MS_WEBHOOK_URL` — URL входящего вебхука МойСклад.
- `APL_WEBHOOK_TIMEOUT` — таймаут HTTP-запросов к МойСклад (сек).
- `APL_WEBHOOK_RETRY_ATTEMPTS` — количество повторов запросов (tenacity).

### Security
- `APL_ALLOWED_ORIGINS` — список CORS origins (JSON-массив строк).
- `APL_API_RATE_LIMIT` — лимит запросов в минуту на одного клиента.

### Logging
- `APL_LOG_LEVEL` — уровень логирования.
- `APL_LOG_FORMAT` — формат логов.

## Структура проекта

- `src/main.py` — точка входа FastAPI, маршруты, middleware.
- `src/core/config.py` — настройки приложения (pydantic settings).
- `src/apps/` — доменные модули (hooks, payment, cashin и т.д.).
- `templates/`, `static/` — HTML шаблоны и статические ресурсы.

## Docker / Docker Compose

- `Dockerfile` — сборка образа (Python 3.11, Poetry, зависимости).
- `docker-compose.yml` — запуск сервиса с монтированием `.env`, `db.sqlite3`, `logs`.
- `entrypoint.sh` — загрузка `.env`, подготовка SQLite и запуск Uvicorn.
