"""Initial load from CS_Reference_Template (sheet Lists) — development helper.

Usage (from backend/):
    python scripts/import_reference_lists.py ../sources/excel/CS_Reference_Template_v0.6.xlsx           (Analyze only)
    python scripts/import_reference_lists.py ../sources/excel/CS_Reference_Template_v0.6.xlsx --apply   (Apply)

Same adapter, engine and report as Settings → Initial data in the app. Running it again changes nothing.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from app.core.errors import AppError
from app.db.base import get_engine, get_sessionmaker
from app.services.excel import initial_load


async def run(path: Path, apply: bool, show_rows: bool) -> int:
    content = await asyncio.to_thread(path.read_bytes)
    async with get_sessionmaker()() as db:
        try:
            report = await initial_load.run(db, content, path.name, None, None, apply=apply)
        except AppError as exc:
            print(json.dumps(exc.params.get("report", {}).get("summary", {}), indent=2))
            print(f"Not applied: {exc.code}", file=sys.stderr)
            return 1
    await get_engine().dispose()
    data = report.as_dict()
    print(
        json.dumps(
            {"applied": data["applied"], "summary": data["summary"], "special_values": data["special_values"]}, indent=2
        )
    )
    for sheet in data["sheets"]:
        print(f"  {sheet['sheet']:<10} {sheet['counts']}")
        if show_rows:
            for row in sheet["rows"]:
                if row["action"] != "unchanged":
                    print(f"     row {row['row']}: {row['key']} {row['action']} {row['errors'] or ''}")
    for issue in data["errors"]:
        print(f"ERROR {issue}", file=sys.stderr)
    return 0 if data["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx", type=Path)
    parser.add_argument("--apply", action="store_true", help="apply (default: analyze only)")
    parser.add_argument("--rows", action="store_true", help="list every row that changes")
    args = parser.parse_args()
    return asyncio.run(run(args.xlsx, args.apply, args.rows))


if __name__ == "__main__":
    sys.exit(main())
