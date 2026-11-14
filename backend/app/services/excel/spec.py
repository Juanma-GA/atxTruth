"""Column specifications. A domain (lists, taxonomy, references...) is a set of sheets; each sheet
declares its stable key and typed columns. Translatable columns expand to `Name [EN]/[ES]/[FR]`."""

from dataclasses import dataclass, field
from enum import StrEnum

from app.core.i18n import SUPPORTED_LANGUAGES

FORMAT_NAME = "atxtruth-excel"
ACTION_HEADER = "_action"
DELETE_ACTION = "delete"
META_SHEET = "_meta"
LOOKUP_SHEET = "_lookups"


class ColumnType(StrEnum):
    TEXT = "text"
    INTEGER = "integer"
    INT_LIST = "int_list"  # "1/3" ↔ [1, 3]
    BOOLEAN = "boolean"  # Yes / No
    REF = "ref"  # code of a row in another sheet of the same domain
    ENUM = "enum"  # one of fixed options
    LIST_ITEM = "list_item"  # code of an item of a value list


@dataclass(frozen=True)
class Column:
    key: str
    header: str
    type: ColumnType = ColumnType.TEXT
    translatable: bool = False
    # Required on creation (for translatable columns: the English text).
    required: bool = False
    max_length: int | None = None
    min: int | None = None
    max: int | None = None
    ref_sheet: str | None = None
    options: tuple[str, ...] = ()
    list_code: str | None = None
    # Exported for information only (e.g. a derived block); changes are ignored with a warning.
    readonly: bool = False
    # Recognise "To complete", "N/A", "None"... as an empty value, with a warning.
    special_values: bool = False
    # Value used on creation when the cell is empty (e.g. Active = Yes).
    default: object = None
    width: int = 18

    def fields(self) -> list[str]:
        """Field ids this column produces: `name.en`, `name.es`... or just `owner`."""
        if self.translatable:
            return [f"{self.key}.{lang}" for lang in SUPPORTED_LANGUAGES]
        return [self.key]

    def header_for(self, field_id: str) -> str:
        if self.translatable:
            return f"{self.header} [{field_id.rsplit('.', 1)[1].upper()}]"
        return self.header


@dataclass(frozen=True)
class SheetSpec:
    name: str
    entity: str
    key: tuple[str, ...]
    columns: tuple[Column, ...]

    def column(self, key: str) -> Column:
        return next(c for c in self.columns if c.key == key)

    def field_headers(self) -> list[tuple[str, str, Column]]:
        """(field id, header, column) in sheet order."""
        return [(f, c.header_for(f), c) for c in self.columns for f in c.fields()]

    def refs(self) -> list[Column]:
        return [c for c in self.columns if c.type == ColumnType.REF]


@dataclass(frozen=True)
class DomainSpec:
    domain: str
    format_version: int
    sheets: tuple[SheetSpec, ...]
    uses_edition: bool = False
    extra: dict[str, str] = field(default_factory=dict)

    def sheet(self, name: str) -> SheetSpec:
        return next(s for s in self.sheets if s.name == name)
