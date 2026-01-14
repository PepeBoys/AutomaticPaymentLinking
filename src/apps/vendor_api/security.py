import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Dict

from src.core.config import settings


class JwtVerificationError(Exception):
    pass


def _get_secret_key() -> str:
    if not settings.ms_vendor_secret_key:
        raise JwtVerificationError("MS vendor secret key is not configured")
    return settings.ms_vendor_secret_key


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(header_b64: str, payload_b64: str, secret: str) -> str:
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return _b64url_encode(signature)


def verify_vendor_jwt(token: str) -> Dict[str, Any]:
    """Проверить подпись JWT от МойСклад (HS256)."""

    try:
        secret = _get_secret_key()
        parts = token.split(".")
        if len(parts) != 3:
            raise JwtVerificationError("Malformed token")

        header_b64, payload_b64, signature_b64 = parts
        expected_sig = _sign(header_b64, payload_b64, secret)
        if not hmac.compare_digest(signature_b64, expected_sig):
            raise JwtVerificationError("Signature verification failed")

        payload_json = _b64url_decode(payload_b64)
        claims = json.loads(payload_json)

        for required in ("exp", "iat", "jti"):
            if required not in claims:
                raise JwtVerificationError(f"Missing claim: {required}")

        now_ts = int(datetime.now(UTC).timestamp())
        if now_ts >= int(claims["exp"]):
            raise JwtVerificationError("Token expired")

        return claims
    except JwtVerificationError:
        raise
    except Exception as exc:  # pragma: no cover - неожиданные ошибки
        raise JwtVerificationError(str(exc)) from exc


def sign_vendor_jwt(
    claims: Dict[str, Any] | None = None,
    expires_in: int = 300,
    secret_override: str | None = None,
) -> str:
    """Подписать JWT для исходящих запросов к Vendor API."""

    secret = secret_override or _get_secret_key()
    now = datetime.now(UTC)
    payload = {
        "iat": int(now.timestamp()),
        "exp": int((now).timestamp()) + expires_in,
        "jti": str(uuid.uuid4()),
        "sub": settings.ms_app_uid,
    }
    if claims:
        payload.update(claims)

    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=",:").encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=",:").encode())
    signature = _sign(header_b64, payload_b64, secret)
    return f"{header_b64}.{payload_b64}.{signature}"


def create_vendor_jwt(expires_in: int = 300) -> str:
    """Создать JWT токен для запросов к Vendor API МойСклад."""
    return sign_vendor_jwt(
        claims={"iss": settings.ms_app_uid},
        expires_in=expires_in,
    )
