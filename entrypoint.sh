#!/usr/bin/env bash
set -euo pipefail

if [ -f "/app/.env" ]; then
  set -a
  . /app/.env
  set +a
fi

if [ -d "/app/db.sqlite3" ]; then
  echo "Error: /app/db.sqlite3 is a directory. Ensure ./db.sqlite3 exists as a file on the host." >&2
  exit 1
fi

touch /app/db.sqlite3
mkdir -p /app/logs

APP_HOST="${APL_HOST:-0.0.0.0}"
APP_PORT="${APL_PORT:-8000}"

exec uvicorn src.main:app --host "${APP_HOST}" --port "${APP_PORT}"
