from sqlalchemy import Boolean, CheckConstraint, Column, String

from src.core.models import Base


class IncomeItemSyncConfig(Base):
    """Настройки фичи автопроставления статьи доходов для аккаунта МС.

    Хранит идентификаторы созданной приложением инфраструктуры: справочник
    «Статьи доходов» и доп. поля контрагента, входящего платежа и приходного
    ордера, ссылающиеся на него.
    """

    ms_account_id = Column(String(64), nullable=False, unique=True, index=True)

    dictionary_id = Column(String(64), nullable=True)
    counterparty_attribute_id = Column(String(64), nullable=True)
    paymentin_attribute_id = Column(String(64), nullable=True)
    cashin_attribute_id = Column(String(64), nullable=True)

    enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    __table_args__ = (
        CheckConstraint(
            "ms_account_id IS NOT NULL AND ms_account_id != ''",
            name="ck_income_sync_account_id_not_empty",
        ),
    )
