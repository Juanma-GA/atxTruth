"""TranslatableText: business text published in EN (master, required), ES and FR (optional).

Stored as JSONB `{"en": "...", "es": "...", "fr": "..."}`. A missing translation is `None` and
must be shown as missing ("No FR translation") — never silently replaced by English (HR7).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator

from app.core.i18n import MASTER_LANGUAGE, SUPPORTED_LANGUAGES, Language


class TranslatableText(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    en: str = Field(min_length=1, max_length=20000)
    es: str | None = Field(default=None, max_length=20000)
    fr: str | None = Field(default=None, max_length=20000)

    @field_validator("en", mode="before")
    @classmethod
    def _master_required(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            raise ValueError("master_language_required")
        return value

    @field_validator("es", "fr", mode="before")
    @classmethod
    def _blank_is_missing(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def get(self, language: Language) -> str | None:
        """The text in `language`, or None when that translation is missing (no silent fallback)."""
        value: str | None = getattr(self, language)
        return value

    def missing_languages(self) -> list[Language]:
        return [lang for lang in SUPPORTED_LANGUAGES if lang != MASTER_LANGUAGE and self.get(lang) is None]

    def to_db(self) -> dict[str, str]:
        return {lang: text for lang in SUPPORTED_LANGUAGES if (text := self.get(lang)) is not None}


class TranslatableTextType(TypeDecorator[TranslatableText]):
    """SQLAlchemy column type: validates on write, returns TranslatableText on read."""

    impl = JSONB
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> dict[str, str] | None:
        if value is None:
            return None
        text = value if isinstance(value, TranslatableText) else TranslatableText.model_validate(value)
        return text.to_db()

    def process_result_value(self, value: Any, dialect: Any) -> TranslatableText | None:
        if value is None:
            return None
        return TranslatableText.model_validate(value)
