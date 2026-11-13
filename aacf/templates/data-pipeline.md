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

# Data Pipeline Template

## Stack
- Language: Python 3.12
- Orchestration: Scheduled tasks (cron / admin console scheduler)
- Data: pandas / polars for processing, asyncpg for DB access
- Storage: PostgreSQL data warehouse, file exports to shared drive

## Project Structure
```
pipeline-name/
├── src/
│   ├── extract/        # Data source connectors
│   ├── transform/      # Processing logic
│   ├── load/           # Destination writers
│   ├── utils/          # Shared utilities
│   ├── config.py       # Configuration
│   └── main.py         # Pipeline entry point
├── tests/
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Design Principles
- Idempotent execution (safe to re-run)
- Checkpointing for long-running pipelines
- Structured logging with correlation IDs
- Error handling with retry + dead-letter queue
- Data validation at boundaries (input/output)
- Classification-aware: respect data classification levels

## Data Classification Rules
- PUBLIC: No restrictions on processing
- INTERNAL: Log access, restrict output destinations
- CONFIDENTIAL: Encrypt at rest, audit all access
- STRICTLY_CONFIDENTIAL: Isolated processing, no bulk export
