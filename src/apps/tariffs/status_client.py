"""Получение подписки аккаунта из Vendor API МС (GET .../apps/{appId}/{accountId}/status)."""

import logging
from typing import Optional

import httpx

from src.core.config import settings

from ..vendor_api.middleware import AppUidAccountMiddleware
from ..vendor_api.security import create_vendor_jwt

logger = logging.getLogger(__name__)


async def fetch_subscription(account_id: str) -> Optional[dict]:
    """Подписка аккаунта ({tariffId, tariffName, trial, expiryMoment}) или None при сбое."""
    url = (
        f"{AppUidAccountMiddleware.VENDOR_API_BASE}/apps/{settings.ms_app_id}"
        f"/{account_id}/status"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url, headers={"Authorization": f"Bearer {create_vendor_jwt()}"}
            )
            resp.raise_for_status()
            subscription = resp.json().get("subscription")
            logger.info(
                "Подписка получена из Vendor API: account_id=%s, subscription=%s",
                account_id,
                subscription,
            )
            return subscription
    except Exception as exc:
        logger.warning(
            "Не удалось получить подписку из Vendor API: account_id=%s, error=%s",
            account_id,
            exc,
        )
        return None
