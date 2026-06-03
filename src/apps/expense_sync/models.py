from sqlalchemy import Boolean, CheckConstraint, Column, Index, String

from src.core.models import Base


class ExpenseItemSyncConfig(Base):
    """Настройки фичи автопроставления статьи расходов для аккаунта МС.

    Хранит идентификаторы созданной приложением инфраструктуры:
    - mirror_customentity_id — id пользовательского справочника-зеркала
      статей расходов;
    - counterparty_attribute_id — id доп. поля контрагента, ссылающегося на
      этот справочник.
    """

    ms_account_id = Column(String(64), nullable=False, unique=True, index=True)

    mirror_customentity_id = Column(String(64), nullable=True)
    counterparty_attribute_id = Column(String(64), nullable=True)

    enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    __table_args__ = (
        CheckConstraint(
            "ms_account_id IS NOT NULL AND ms_account_id != ''",
            name="ck_expense_sync_account_id_not_empty",
        ),
    )


class ExpenseItemMapping(Base):
    """Соответствие статьи расходов и элемента справочника-зеркала.

    Локальная таблица соответствий (источник истины для синхронизации в обе
    стороны), чтобы не перезаписывать пользовательский externalCode у самих
    expenseitem.
    """

    ms_account_id = Column(String(64), nullable=False, index=True)
    expenseitem_id = Column(String(64), nullable=False, index=True)
    customentity_element_id = Column(String(64), nullable=False, index=True)

    __table_args__ = (
        Index(
            "ix_expense_mapping_account_item",
            "ms_account_id",
            "expenseitem_id",
            unique=True,
        ),
        Index(
            "ix_expense_mapping_account_element",
            "ms_account_id",
            "customentity_element_id",
            unique=True,
        ),
    )
