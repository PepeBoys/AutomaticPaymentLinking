"""Доп. поля типа «справочник» (customentity) у любых сущностей МойСклад."""

from typing import Optional


def extract_customentity_id(href: str) -> Optional[str]:
    """Извлечь id справочника из customEntityMeta.href.

    МС использует два вида ссылок:
    - .../entity/customentity/{id}/metadata
    - .../context/companysettings/metadata/customEntities/{id}
    """
    if not href:
        return None
    if "/customEntities/" in href:
        return href.split("/customEntities/")[-1].split("/")[0]
    if "/customentity/" in href:
        return href.split("/customentity/")[-1].split("/")[0]
    return None


def find_customentity_attribute(attributes: list[dict], name: str) -> Optional[dict]:
    """Найти доп. поле типа «справочник» по имени.

    Возвращает копию сырого объекта доп. поля с дополнительным ключом
    ``customentity_id`` — id справочника, на который ссылается поле.
    """
    for attr in attributes:
        if attr.get("type") == "customentity" and attr.get("name") == name:
            attr = dict(attr)
            href = attr.get("customEntityMeta", {}).get("href", "")
            attr["customentity_id"] = extract_customentity_id(href)
            return attr
    return None


def build_customentity_attribute_payload(
    base_url: str,
    name: str,
    customentity_metadata_id: str,
    *,
    required: bool = False,
    show: bool = True,
) -> dict:
    """Тело запроса на создание доп. поля, ссылающегося на справочник."""
    return {
        "name": name,
        "type": "customentity",
        "required": required,
        "show": show,
        "customEntityMeta": {
            "href": f"{base_url}/entity/customentity/{customentity_metadata_id}/metadata",
            "type": "customentitymetadata",
            "mediaType": "application/json",
        },
    }
