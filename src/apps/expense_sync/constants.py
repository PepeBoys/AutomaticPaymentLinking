"""Константы модуля синхронизации статей расходов."""

# Наименование пользовательского справочника-зеркала статей расходов.
MIRROR_DICTIONARY_NAME = "Статьи расходов"

# Наименование доп. поля контрагента, ссылающегося на справочник-зеркало.
COUNTERPARTY_ATTRIBUTE_NAME = "Статья расходов"

# entityType для вебхуков синхронизации.
EXPENSEITEM_ENTITY_TYPE = "expenseitem"
CUSTOMENTITY_ENTITY_TYPE = "customentity"

# Действия, на которые подписываемся для двусторонней синхронизации.
SYNC_WEBHOOK_ACTIONS = ("CREATE", "UPDATE", "DELETE")

# Документы, для которых проставляем статью расходов (этап 4 фичи).
# Вебхуки на их создание нужны, чтобы автопроставление работало независимо от
# автопривязки платежей.
EXPENSE_PAYMENT_ENTITY_TYPES = ("paymentout", "cashout")
EXPENSE_PAYMENT_WEBHOOK_ACTION = "CREATE"
