from app.core.codes import CATALOGUE_CODE_RE, SLUG_RE, natural_key, slugify
from app.core.field_state import FieldState, recognise


def test_natural_order() -> None:
    codes = ["S1.10", "S1.2", "S10.1", "S2.1", "S1.1.1", "P-S2.6.1", "F1.1"]
    assert sorted(codes, key=natural_key) == ["F1.1", "S1.1.1", "S1.2", "S1.10", "S2.1", "P-S2.6.1", "S10.1"]
    assert sorted(["P-F2.6", "F2.6", "F2.10", "F2.5"], key=natural_key) == ["F2.5", "F2.6", "P-F2.6", "F2.10"]
    assert sorted(["SOL-10", "SOL-2", "SOL-1"], key=natural_key) == ["SOL-1", "SOL-2", "SOL-10"]


def test_slugify() -> None:
    assert slugify("FO + BO") == "fo_bo"
    assert slugify("IQP 3.1") == "iqp_3_1"
    assert slugify("Life Sciences") == "life_sciences"
    assert slugify("Défense") == "defense"
    assert all(SLUG_RE.fullmatch(slugify(s)) for s in ["To check", "Worldwide deployment", "PoC"])


def test_catalogue_codes() -> None:
    for code in ["B1", "F1.1", "P-F2.6", "S1.1.1", "P-S2.6.3", "SOL-8", "ADJ-7"]:
        assert CATALOGUE_CODE_RE.fullmatch(code)
    for code in ["", "S 1", "-B1", "B1-", "S1/2"]:
        assert not CATALOGUE_CODE_RE.fullmatch(code)


def test_field_states() -> None:
    assert recognise(None) == FieldState.TO_COMPLETE
    assert recognise("  ") == FieldState.TO_COMPLETE
    assert recognise("To complete") == FieldState.TO_COMPLETE
    assert recognise("N/A") == FieldState.NOT_APPLICABLE
    assert recognise("None") == FieldState.NONE
    assert recognise("No packaged solution") == FieldState.NONE
    assert recognise("To check") is None  # a normal item in yes_no_check / scope
    assert recognise("Aerospace") is None
