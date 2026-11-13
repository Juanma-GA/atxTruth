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

# Internal Tool Template

## Stack
- Backend: Python 3.12 + FastAPI (or CLI with Click/Typer)
- Frontend (if UI needed): React 18 + Vite
- Auth: Keycloak SSO
- Deployment: Docker container on shared infrastructure

## Project Structure
```
tool-name/
├── app/
│   ├── core/           # Core tool logic
│   ├── api/            # API endpoints (if web-based)
│   ├── cli/            # CLI commands (if CLI-based)
│   ├── config.py       # Configuration
│   └── main.py         # Entry point
├── tests/
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Requirements
- Must be registered in the AI Tool Registry before deployment
- Risk assessment completed (auto-detected from capabilities)
- Training completed by all intended users
- IS review for elevated/high risk tools

## Deployment Path
- T1: Local developer machine only
- T2: Shared VM (IT provisions, IS deploys)
- T3: Dedicated VM with DW access
- T4: Production infrastructure (IS + IT joint)
