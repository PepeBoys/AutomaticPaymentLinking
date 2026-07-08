"""Пользовательские шаблоны назначения платежа.

Шаблон — строка из литерального текста и переменных:
  $name   — номер документа (обязательна, ровно одна);
  $moment — дата документа (опциональна, не более одной).

Литеральный текст служит якорем: поиск идёт подстрокой без учёта регистра,
последовательности пробелов приравниваются друг к другу. $name захватывает
текст нежадно до следующего литерала, а в конце шаблона — одно слово без
пробелов. Если в шаблоне есть $moment, дата обязана присутствовать в тексте,
иначе шаблон считается несовпавшим.

Шаблоны применяются по порядку (порядок = приоритет), выигрывает первый
совпавший. Fallback-эвристик нет: не совпал ни один шаблон — данные не
извлечены.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

MAX_TEMPLATES = 10
MAX_TEMPLATE_LENGTH = 256

# Только ASCII в имени переменной: кириллица сразу после $name должна
# трактоваться как литеральный текст, а не как часть имени переменной
# (иначе поведение разойдётся с JS-валидацией на фронте, где \w — ASCII).
_VAR_RE = re.compile(r"\$([a-zA-Z_][a-zA-Z0-9_]*)")
_KNOWN_VARS = ("name", "moment")

_MOMENT_PATTERN = r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"
_MOMENT_FORMATS = ("%d.%m.%Y", "%d.%m.%y", "%d-%m-%Y", "%d/%m/%Y")


@dataclass
class PurposeExtraction:
    """Результат извлечения данных из назначения платежа."""

    name: str
    moment: Optional[datetime]
    template: str
    template_index: int


def validate_template(template: str) -> list[str]:
    """Проверить один шаблон, вернуть список ошибок (пустой — шаблон валиден)."""

    errors: list[str] = []
    stripped = template.strip()

    if not stripped:
        return ["шаблон не может быть пустым"]

    if len(stripped) > MAX_TEMPLATE_LENGTH:
        errors.append(f"длина шаблона не должна превышать {MAX_TEMPLATE_LENGTH} символов")

    matches = list(_VAR_RE.finditer(stripped))
    var_names = [match.group(1) for match in matches]

    unknown = sorted({name for name in var_names if name not in _KNOWN_VARS})
    if unknown:
        errors.append(
            "неизвестные переменные: " + ", ".join(f"${name}" for name in unknown)
        )

    name_count = var_names.count("name")
    if name_count == 0:
        errors.append("шаблон должен содержать переменную $name")
    elif name_count > 1:
        errors.append("переменная $name должна встречаться ровно один раз")

    if var_names.count("moment") > 1:
        errors.append("переменная $moment может встречаться не более одного раза")

    for prev, current in zip(matches, matches[1:]):
        if not stripped[prev.end():current.start()].strip():
            errors.append("между переменными должен быть литеральный текст")
            break

    return errors


def validate_templates(templates: list[str]) -> list[str]:
    """Проверить список шаблонов для сохранения настроек."""

    errors: list[str] = []

    if not templates:
        return ["нужен хотя бы один шаблон назначения платежа"]

    if len(templates) > MAX_TEMPLATES:
        errors.append(f"допускается не более {MAX_TEMPLATES} шаблонов")

    seen: set[str] = set()
    for index, template in enumerate(templates, start=1):
        for error in validate_template(template):
            errors.append(f"шаблон {index}: {error}")

        key = " ".join(template.split()).casefold()
        if key in seen:
            errors.append(f"шаблон {index}: дублирует другой шаблон")
        seen.add(key)

    return errors


def _escape_literal(literal: str) -> str:
    """Экранировать литеральный кусок шаблона, приравнивая пробельные серии."""

    words = literal.split()
    if not words:
        return r"\s+" if literal else ""

    pattern = r"\s+".join(re.escape(word) for word in words)
    if literal[0].isspace():
        pattern = r"\s+" + pattern
    if literal[-1].isspace():
        pattern = pattern + r"\s+"
    return pattern


def build_template_regex(template: str) -> re.Pattern:
    """Скомпилировать валидный шаблон в регулярное выражение."""

    stripped = template.strip()
    matches = list(_VAR_RE.finditer(stripped))

    parts: list[str] = []
    cursor = 0
    for index, match in enumerate(matches):
        parts.append(_escape_literal(stripped[cursor:match.start()]))

        if match.group(1) == "name":
            is_last_token = index == len(matches) - 1 and match.end() == len(stripped)
            parts.append(r"(?P<name>\S+)" if is_last_token else r"(?P<name>.+?)")
        else:
            parts.append(rf"(?P<moment>{_MOMENT_PATTERN})")

        cursor = match.end()

    parts.append(_escape_literal(stripped[cursor:]))

    return re.compile("".join(parts), re.IGNORECASE)


def parse_moment(moment_str: Optional[str]) -> Optional[datetime]:
    """Распарсить дату из назначения платежа."""

    if not moment_str:
        return None

    for fmt in _MOMENT_FORMATS:
        try:
            return datetime.strptime(moment_str, fmt)
        except ValueError:
            pass

    return None


def _try_extract(template: str, payment_purpose: str) -> Optional[dict]:
    """Применить один валидный шаблон; None — шаблон не совпал."""

    match = build_template_regex(template).search(payment_purpose)
    if not match:
        return None

    name = (match.groupdict().get("name") or "").strip()
    if not name:
        return None

    moment = None
    moment_str = match.groupdict().get("moment")
    if moment_str is not None:
        moment = parse_moment(moment_str)
        if moment is None:
            # $moment указан в шаблоне — дата обязана быть корректной.
            return None

    return {"name": name, "moment": moment}


def extract_from_templates(
    payment_purpose: Optional[str], templates: list[str]
) -> Optional[PurposeExtraction]:
    """Извлечь номер документа и дату первым совпавшим шаблоном."""

    if not payment_purpose:
        return None

    for index, template in enumerate(templates):
        if validate_template(template):
            logger.warning(
                "Пропущен невалидный шаблон назначения платежа №%d: '%s'",
                index + 1,
                template,
            )
            continue

        extracted = _try_extract(template, payment_purpose)
        if extracted:
            return PurposeExtraction(
                name=extracted["name"],
                moment=extracted["moment"],
                template=template,
                template_index=index,
            )

    return None


def test_templates(payment_purpose: str, templates: list[str]) -> list[dict]:
    """Прогнать текст назначения по каждому шаблону (для проверки в UI)."""

    results = []
    for template in templates:
        errors = validate_template(template)
        result = {
            "template": template,
            "valid": not errors,
            "errors": errors,
            "matched": False,
            "name": None,
            "moment": None,
        }

        if not errors and payment_purpose:
            extracted = _try_extract(template, payment_purpose)
            if extracted:
                result["matched"] = True
                result["name"] = extracted["name"]
                if extracted["moment"]:
                    result["moment"] = extracted["moment"].strftime("%d.%m.%Y")

        results.append(result)

    return results


def normalize_masks_input(value) -> list[str]:
    """Привести значение из API (строка, список или None) к списку шаблонов."""

    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    return [
        str(item).strip()
        for item in value
        if item is not None and str(item).strip()
    ]


def masks_from_db(raw: Optional[str]) -> list[str]:
    """Раскодировать шаблоны из колонки БД (JSON-массив или legacy-строка)."""

    if not raw or not raw.strip():
        return []

    stripped = raw.strip()
    if stripped.startswith("["):
        try:
            data = json.loads(stripped)
        except ValueError:
            data = None
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]

    return [stripped]


def masks_to_db(masks: Optional[list[str]]) -> Optional[str]:
    """Закодировать шаблоны в JSON для колонки БД (пустой список — NULL)."""

    cleaned = [mask.strip() for mask in (masks or []) if mask and mask.strip()]
    if not cleaned:
        return None
    return json.dumps(cleaned, ensure_ascii=False)
