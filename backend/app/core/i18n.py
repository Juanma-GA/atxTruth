"""Languages the product supports (interface and content). EN is the master content language."""

from typing import Literal

Language = Literal["en", "es", "fr"]
SUPPORTED_LANGUAGES: tuple[Language, ...] = ("en", "es", "fr")
MASTER_LANGUAGE: Language = "en"
