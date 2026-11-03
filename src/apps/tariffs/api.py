"""REST API тарифов."""

from fastapi import APIRouter

from ..ms_auth.dependencies import AuthSvcDep
from .constants import FEATURE_LABELS
from .dependencies import TariffSvcDep
from .schemas import FeatureStatus, TariffResponse

router = APIRouter()


@router.get("", response_model=TariffResponse)
async def get_tariff(auth_service: AuthSvcDep, tariffs: TariffSvcDep):
    """Текущий тариф аккаунта и доступность функций (для блокировки в интерфейсе)."""
    tariff = await tariffs.get_account_tariff(auth_service.get_account_id())
    features = {
        key: FeatureStatus(
            label=label,
            available=key in tariff.features,
            required_tariffs=tariffs.required_tariff_names(key),
            message=None if key in tariff.features else tariffs.locked_message(key),
        )
        for key, label in FEATURE_LABELS.items()
    }
    return TariffResponse(
        tariffs_enabled=tariff.tariffs_enabled,
        known=tariff.known,
        tariff_name=tariff.tariff_name,
        trial=tariff.trial,
        expiry=tariff.expiry,
        features=features,
    )
