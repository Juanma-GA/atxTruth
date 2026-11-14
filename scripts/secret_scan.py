"""Secret scan that fails only on NEW secrets (AACF G1/G2), never because lines moved.

Usage (from the repository root, with the backend's Python):
    backend/.venv/bin/python scripts/secret_scan.py           (Windows: backend\\.venv\\Scripts\\python)

Scans every tracked and untracked-but-not-ignored file with the plugins and filters stored in
.secrets.baseline, and compares findings by (file, type, secret hash) — line numbers are ignored.
The baseline is never rewritten. Known false positives are marked in place with
`pragma: allowlist secret` (or `pragma: allowlist nextline secret` on the line above); only files
that cannot hold comments (the i18n JSON) keep entries in the baseline.

To accept a new false positive that cannot take a pragma, regenerate the baseline on purpose:
    backend/.venv/bin/python -m detect_secrets scan --exclude-files '<regex from the baseline>' > .secrets.baseline
Exit codes: 0 no new secrets · 1 new secrets found · 2 detect-secrets missing.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / ".secrets.baseline"


def candidate_files() -> list[str]:
    def git(*args: str) -> list[str]:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)  # noqa: S603, S607
        return [line for line in out.stdout.splitlines() if line]

    files = set(git("ls-files")) | set(git("ls-files", "--others", "--exclude-standard"))
    # The baseline holds the hashes themselves; detect-secrets' own CLI skips it too.
    return sorted(f for f in files if (ROOT / f).is_file() and f != BASELINE.name)


def main() -> int:
    try:
        from detect_secrets.core import baseline
        from detect_secrets.core.secrets_collection import SecretsCollection
    except ImportError:
        print("detect-secrets is not installed in this Python (it is in backend/requirements-dev.lock.txt).")
        return 2

    known_collection = baseline.load(baseline.load_from_file(str(BASELINE)), str(BASELINE))  # also loads plugins/filters
    known = {(name, secret.type, secret.secret_hash) for name, secret in known_collection}

    current = SecretsCollection(root=str(ROOT))
    current.scan_files(*candidate_files())

    new = sorted(
        (name, secret.line_number, secret.type)
        for name, secret in current
        if (name, secret.type, secret.secret_hash) not in known
    )
    if new:
        print(f"Possible NEW secrets ({len(new)}):")
        for name, line, kind in new:
            print(f"  {name}:{line}  {kind}")
        print("Remove the secret, or mark a false positive in place with `pragma: allowlist secret`.")
        return 1
    print(f"secret scan: no new secrets ({len(known)} known false positives, compared without line numbers).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
