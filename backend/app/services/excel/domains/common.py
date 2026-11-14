"""Helpers shared by domain handlers."""

from typing import Any

from app.core.i18n import SUPPORTED_LANGUAGES
from app.schemas.translatable import TranslatableText


def tt_fields(prefix: str, text: TranslatableText | None) -> dict[str, Any]:
    """TranslatableText → {"name.en": ..., "name.es": ..., "name.fr": ...}."""
    return {f"{prefix}.{lang}": (text.get(lang) if text else None) for lang in SUPPORTED_LANGUAGES}


def tt_from(prefix: str, fields: dict[str, Any], current: TranslatableText | None = None) -> TranslatableText | None:
    """Builds a TranslatableText from field values, keeping languages not given from `current`."""
    data: dict[str, Any] = current.to_db() if current else {}
    for lang in SUPPORTED_LANGUAGES:
        key = f"{prefix}.{lang}"
        if key in fields:
            data[lang] = fields[key]
    data = {k: v for k, v in data.items() if v}
    if not data:
        return None
    return TranslatableText.model_validate(data)


def touches(prefix: str, changes: dict[str, Any]) -> bool:
    return any(k.startswith(f"{prefix}.") for k in changes)
