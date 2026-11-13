# Historial de cambios

Una entrada corta por encargo: qué, por qué, commit y tests. Las entradas nuevas van al final.

## E0 — Andamiaje (13/11/2026)

- **Qué**: AACF 2.0.0 en `aacf/`; backend FastAPI + Postgres (usuarios, roles admin/editor/viewer, login local con JWT RS256 y refresh en cookie HttpOnly con rotación, `AuthProvider` para SSO, ajustes funcionales con validación por tipo y mezcla profunda, auditoría); frontend React con tokens DTCG → CSS/Tailwind (OKLCH, claro/oscuro), shell del mockup, i18n EN/ES/FR, `TranslatableText` con su editor; `npm run check`, `verify-e0`, pre-commit y CI.
- **Por qué**: base sobre la que se construyen E1–F2 con el AACF cumplido desde el primer commit.
- **Commits**: rama `feature/e0-andamiaje` (ver PR).
- **Tests**: `npm run check` (58 pytest, 26 vitest, eslint, ruff, tsc, mypy estricto, build, patrones prohibidos) y `verify-e0` 26/26 con capturas.
