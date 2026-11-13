import pytest
from pydantic import ValidationError
from sqlalchemy import Column, Integer, MetaData, Table, insert, select

from app.db.base import get_engine
from app.schemas.translatable import TranslatableText, TranslatableTextType


def test_master_language_is_required() -> None:
    with pytest.raises(ValidationError):
        TranslatableText.model_validate({"es": "Hola"})
    with pytest.raises(ValidationError):
        TranslatableText.model_validate({"en": "   "})


def test_missing_translations_are_none_not_english() -> None:
    text = TranslatableText.model_validate({"en": "Hello", "es": "  ", "fr": None})
    assert text.get("es") is None
    assert text.get("fr") is None
    assert text.missing_languages() == ["es", "fr"]
    assert text.to_db() == {"en": "Hello"}


def test_unknown_languages_rejected() -> None:
    with pytest.raises(ValidationError):
        TranslatableText.model_validate({"en": "Hello", "de": "Hallo"})


def test_complete_text_has_no_missing_languages() -> None:
    text = TranslatableText(en="Hello", es="Hola", fr="Bonjour")
    assert text.missing_languages() == []
    assert text.get("fr") == "Bonjour"


async def test_column_type_round_trip() -> None:
    metadata = MetaData()
    table = Table(
        "tmp_translatable", metadata, Column("id", Integer, primary_key=True), Column("title", TranslatableTextType())
    )
    async with get_engine().begin() as conn:
        await conn.run_sync(metadata.create_all)
        try:
            await conn.execute(insert(table).values(id=1, title={"en": "Hello", "fr": "Bonjour", "es": ""}))
            stored = (await conn.execute(select(table.c.title))).scalar_one()
            assert stored == TranslatableText(en="Hello", fr="Bonjour")
            with pytest.raises(Exception, match="master_language_required"):
                await conn.execute(insert(table).values(id=2, title={"en": " "}))
        finally:
            await conn.run_sync(metadata.drop_all)
