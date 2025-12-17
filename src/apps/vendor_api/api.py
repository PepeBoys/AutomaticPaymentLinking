import logging

from fastapi import APIRouter, Depends, HTTPException, status

from .dependencies import AuthHeader, get_vendor_activation_service, get_vendor_service
from .schemas import ActivationPayload, ActivationResponse, VendorEventPayload
from .services import VendorApiService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/moysklad/vendor/1.0/apps")


@router.put("/{app_id}/{account_id}", response_model=ActivationResponse)
async def activate_solution(
    app_id: str,
    account_id: str,
    payload: ActivationPayload,
    authorization: AuthHeader,
    service: VendorApiService = Depends(get_vendor_activation_service),
):
    print(f"[app_id] -> {app_id}")
    print(f"[account_id] -> {account_id}")
    print(f"[payload] -> {payload}")
    print(f"[authorization] -> {authorization}")
    token = _extract_bearer(authorization)
    return await service.activate_app(app_id, account_id, payload, token)


@router.delete("/{app_id}/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_solution(
    app_id: str,
    account_id: str,
    authorization: AuthHeader,
    service: VendorApiService = Depends(get_vendor_service),
):
    token = _extract_bearer(authorization)
    await service.deactivate_app(app_id, account_id, token)


@router.put("/{app_id}/{account_id}/event", status_code=status.HTTP_202_ACCEPTED)
async def receive_event(
    app_id: str,
    account_id: str,
    payload: VendorEventPayload,
    authorization: AuthHeader,
    service: VendorApiService = Depends(get_vendor_service),
):
    print(f"[app_id] -> {app_id}")
    print(f"[account_id] -> {account_id}")
    print(f"[payload] -> {payload}")
    print(f"[authorization] -> {authorization}")
    token = _extract_bearer(authorization)
    service._validate_app_id(app_id)  # type: ignore[attr-defined]
    service._verify_jwt(token)  # type: ignore[attr-defined]
    logger.info(
        "Received vendor event: app=%s account=%s type=%s", app_id, account_id, payload.eventType
    )
    return {"status": "accepted"}


def _extract_bearer(header: str | None) -> str:
    if not header or not header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
        )
    return header.split(" ", 1)[1]