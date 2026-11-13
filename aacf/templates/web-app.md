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

# Web Application Template

## Stack
- Frontend: React 18 + TypeScript + Vite 6
- Styling: Tailwind CSS 4 + shadcn/ui
- State: Zustand
- Backend: FastAPI + SQLAlchemy 2.0 async
- Database: PostgreSQL 16
- Auth: Keycloak OIDC

## Project Structure
```
project-name/
├── frontend/
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page-level components
│   │   ├── services/       # API client layer
│   │   ├── stores/         # Zustand stores
│   │   ├── hooks/          # Custom React hooks
│   │   └── types/          # TypeScript types
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.ts
├── backend/
│   ├── app/
│   │   ├── api/            # Route handlers
│   │   ├── db/             # Models + session
│   │   ├── services/       # Business logic
│   │   ├── auth/           # OIDC integration
│   │   ├── config.py       # Settings
│   │   └── main.py         # FastAPI app
│   ├── pyproject.toml
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Security Checklist
- [ ] OIDC authentication configured
- [ ] CORS restricted to known origins
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (React default escaping)
- [ ] CSRF protection
- [ ] Rate limiting on sensitive endpoints
- [ ] Secrets in environment variables, not code
