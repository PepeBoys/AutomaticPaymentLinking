from sqlalchemy import Column, String

from src.core.models import Base


class DocumentItemsConfig(Base):
    """Настройки проставления статей доходов/расходов в документы для аккаунта МС.

    Хранит режимы (off / linked / chain) и id доп. полей «Статья доходов» /
    «Статья расходов», созданных приложением в каждом типе документа.
    """

    ms_account_id = Column(String(64), nullable=False, unique=True, index=True)

    income_mode = Column(String(16), nullable=False, default="off", server_default="off")
    expense_mode = Column(String(16), nullable=False, default="off", server_default="off")

    customerorder_attribute_id = Column(String(64), nullable=True)
    invoiceout_attribute_id = Column(String(64), nullable=True)
    demand_attribute_id = Column(String(64), nullable=True)
    purchaseorder_attribute_id = Column(String(64), nullable=True)
    invoicein_attribute_id = Column(String(64), nullable=True)
    supply_attribute_id = Column(String(64), nullable=True)
