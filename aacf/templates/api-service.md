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

# API Service Template

## Stack
- Runtime: Python 3.12 / .NET 8 / Node.js 20
- Framework: FastAPI / ASP.NET Core / Express
- Auth: Keycloak OIDC + API key support
- Database: PostgreSQL 16 (if persistent state needed)
- Caching: Redis (if applicable)

## Project Structure
```
service-name/
├── app/
│   ├── api/            # Route handlers (versioned: /v1/)
│   ├── models/         # Data models / DTOs
│   ├── services/       # Business logic
│   ├── middleware/     # Auth, logging, rate limiting
│   ├── config.py       # Settings
│   └── main.py         # App entry
├── tests/
├── pyproject.toml
├── Dockerfile
└── README.md
```

## API Design Rules
- RESTful endpoints with proper HTTP methods
- JSON request/response bodies
- Pagination for list endpoints (limit/offset)
- Consistent error format: `{"detail": "message", "code": "ERROR_CODE"}`
- API versioning via URL prefix (/api/v1/)
- OpenAPI/Swagger documentation auto-generated

## Security Requirements
- Bearer token auth (Keycloak) or API key
- Rate limiting per client
- Input validation (Pydantic models)
- No sensitive data in logs
- HTTPS only in production
