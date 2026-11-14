"""States of a field that are not values (project convention, E1).

Excel cells such as "To complete", "N/A" or "None" are not list items nor entities: they say why a
field has no value. Importers recognise them, count them in the report and never treat them as
errors. How each reference field stores them is decided in E2.
"""

from enum import StrEnum


class FieldState(StrEnum):
    TO_COMPLETE = "to_complete"  # "To complete" or an empty cell: data still missing
    NOT_APPLICABLE = "not_applicable"  # "N/A"
    NONE = "none"  # "None" / "No packaged solution"
    UNMAPPED = "unmapped"  # adjacent column "To check" ("No ADJ entry fits")


# Texts recognised in any column that accepts special values (case-insensitive, trimmed).
GENERIC_SPECIAL_VALUES: dict[str, FieldState] = {
    "to complete": FieldState.TO_COMPLETE,
    "n/a": FieldState.NOT_APPLICABLE,
    "none": FieldState.NONE,
    "no packaged solution": FieldState.NONE,
}


def recognise(raw: object) -> FieldState | None:
    if raw is None:
        return FieldState.TO_COMPLETE
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return FieldState.TO_COMPLETE
        return GENERIC_SPECIAL_VALUES.get(text.lower())
    return None
