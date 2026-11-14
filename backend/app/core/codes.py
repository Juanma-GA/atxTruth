"""Stable codes: natural ordering, slugs and validation."""

import re
import unicodedata

_CHUNK = re.compile(r"(\d+)")
# List and item codes: snake_case (sector, iqp_3_1, fo_bo).
SLUG_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
# Catalogue codes: B1, F1.1, P-F2.6, S1.1.1, SOL-1, ADJ-1.
CATALOGUE_CODE_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.\-]{0,30}[A-Za-z0-9])?$")


# Proposed items carry a "P-" prefix (P-F2.6, P-S2.6.1): they sort where their number puts them.
PROPOSED_PREFIX = "P-"


def natural_key(code: str) -> tuple[tuple[int, int | str], ...]:
    """Sort key where digit runs compare as numbers: S1.2 < S1.10; P-F2.6 right after F2.5/F2.6."""
    proposed = code.upper().startswith(PROPOSED_PREFIX)
    base = code[len(PROPOSED_PREFIX) :] if proposed else code
    parts = tuple((0, int(part)) if part.isdigit() else (1, part.lower()) for part in _CHUNK.split(base) if part)
    return (*parts, (0, 1 if proposed else 0))


def slugify(text: str) -> str:
    """'FO + BO' → 'fo_bo', 'IQP 3.1' → 'iqp_3_1', 'Défense' → 'defense'."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")
