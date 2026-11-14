"""The import report: what Analyze found and what Apply did, sheet by sheet and row by row."""

from dataclasses import dataclass, field
from typing import Any, Literal

RowAction = Literal["create", "update", "delete", "unchanged", "error"]
_COUNTED: tuple[RowAction, ...] = ("create", "update", "delete", "unchanged")


@dataclass
class Issue:
    code: str
    column: str | None = None
    params: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "column": self.column, "params": self.params}


@dataclass
class Change:
    field: str
    column: str
    before: Any
    after: Any


@dataclass
class RowReport:
    sheet: str
    row: int | None
    key: str
    action: RowAction
    changes: list[Change] = field(default_factory=list)
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)


@dataclass
class SheetReport:
    sheet: str
    rows: list[RowReport] = field(default_factory=list)
    not_in_file: list[str] = field(default_factory=list)
    present: bool = True

    def count(self, action: RowAction) -> int:
        return sum(1 for r in self.rows if r.action == action)


@dataclass
class Report:
    domain: str
    file_name: str | None
    sheets: list[SheetReport] = field(default_factory=list)
    errors: list[Issue] = field(default_factory=list)  # file-level (wrong domain, missing sheet...)
    warnings: list[Issue] = field(default_factory=list)
    special_values: dict[str, dict[str, int]] = field(default_factory=dict)  # state → column → count
    applied: bool = False

    @property
    def has_errors(self) -> bool:
        return bool(self.errors) or any(r.errors for s in self.sheets for r in s.rows)

    def count_special(self, state: str, column: str) -> None:
        by_column = self.special_values.setdefault(state, {})
        by_column[column] = by_column.get(column, 0) + 1

    def summary(self) -> dict[str, int]:
        rows = [r for s in self.sheets for r in s.rows]
        return {
            "create": sum(1 for r in rows if r.action == "create"),
            "update": sum(1 for r in rows if r.action == "update"),
            "delete": sum(1 for r in rows if r.action == "delete"),
            "unchanged": sum(1 for r in rows if r.action == "unchanged"),
            "error_rows": sum(1 for r in rows if r.errors),
            "errors": len(self.errors) + sum(len(r.errors) for r in rows),
            "warnings": len(self.warnings) + sum(len(r.warnings) for r in rows),
            "not_in_file": sum(len(s.not_in_file) for s in self.sheets),
            "special_values": sum(sum(c.values()) for c in self.special_values.values()),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "file_name": self.file_name,
            "applied": self.applied,
            "ok": not self.has_errors,
            "summary": self.summary(),
            "errors": [i.as_dict() for i in self.errors],
            "warnings": [i.as_dict() for i in self.warnings],
            "special_values": self.special_values,
            "sheets": [
                {
                    "sheet": s.sheet,
                    "present": s.present,
                    "counts": {a: s.count(a) for a in _COUNTED}
                    | {"error_rows": sum(1 for r in s.rows if r.errors), "not_in_file": len(s.not_in_file)},
                    "not_in_file": s.not_in_file,
                    "rows": [
                        {
                            "row": r.row,
                            "key": r.key,
                            "action": "error" if r.errors else r.action,
                            "changes": [
                                {"field": c.field, "column": c.column, "before": c.before, "after": c.after}
                                for c in r.changes
                            ],
                            "errors": [i.as_dict() for i in r.errors],
                            "warnings": [i.as_dict() for i in r.warnings],
                        }
                        for r in s.rows
                    ],
                }
                for s in self.sheets
            ],
        }
