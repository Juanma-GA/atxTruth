<!-- ═══ AACF VERSION CHECK — AGENTS READ FIRST ═══
This file belongs to a downloaded snapshot of the ATEXIS AI Framework, version 2.0.0.
Before relying on it, verify the snapshot is current:
1. Call the aacf_fetch MCP tool (endpoint http://10.117.139.1:8200/mcp, streamable-http,
   header 'Authorization: Bearer <key>' or 'X-Api-Key: <key>'):
   aacf_fetch({"path": "VERSION"})
2. If the returned version differs from 2.0.0, this snapshot is OUTDATED. Fetch ALL
   framework files fresh via aacf_fetch (start with aacf_fetch({"path": "", "list_dir": true})
   and walk the tree), or ask the user to re-download the framework ZIP from the IdAI
   portal (/propose/framework). Do not mix files from different versions.
3. If you CANNOT reach the aacf_fetch MCP, you MUST tell the user: you cannot reach the
   AACF MCP and may be working with an outdated version of the framework. Then proceed
   with this file as-is.
Verify once per session, not per file.
═══ -->

# Automation Script Template

## Stack
- Language: Python 3.12 / PowerShell 7 / Bash
- Scheduling: Admin console scheduled tasks
- Logging: Structured JSON to stdout (captured by scheduler)

## Project Structure
```
script-name/
├── src/
│   ├── main.py         # Entry point
│   ├── config.py       # Configuration from env
│   └── utils.py        # Shared utilities
├── tests/
├── pyproject.toml      # (if Python)
└── README.md
```

## Guidelines
- Single responsibility: one script = one task
- Idempotent: safe to re-run without side effects
- Exit codes: 0 = success, 1 = error, 2 = warning
- Structured output: JSON to stdout for downstream processing
- No hardcoded credentials: use env vars or Keycloak service accounts
- Timeout: define max execution time in scheduler config
- Alerting: emit error events that trigger admin console alerts

## Approval
- T1: Self-service (local only)
- T2+: Requires IS review before scheduling
