# Historial de cambios

Una entrada corta por encargo: qué, por qué, commit y tests. Las entradas nuevas van al final.

## E0 — Andamiaje (13/11/2026)

- **Qué**: AACF 2.0.0 en `aacf/`; backend FastAPI + Postgres (usuarios, roles admin/editor/viewer, login local con JWT RS256 y refresh en cookie HttpOnly con rotación, `AuthProvider` para SSO, ajustes funcionales con validación por tipo y mezcla profunda, auditoría); frontend React con tokens DTCG → CSS/Tailwind (OKLCH, claro/oscuro), shell del mockup, i18n EN/ES/FR, `TranslatableText` con su editor; `npm run check`, `verify-e0`, pre-commit y CI.
- **Por qué**: base sobre la que se construyen E1–F2 con el AACF cumplido desde el primer commit.
- **Commits**: `cf59319`, `c8b7be0`, `2eab4a4` (rama `feature/e0-andamiaje`, PR #1), fusionados en `main` con `c299a78`.
- **Revisión**: agente `code-reviewer` del AACF (contexto aislado): aprobado, sin bloqueantes. Arreglado: CSP `style-src` alineada con la decisión, límite de login seguro ante peticiones concurrentes, bcrypt siempre (sin fuga por tiempo de cuentas desactivadas), contraseñas sin recortar, bloqueo de filas al comprobar el último admin. Aceptado y documentado en `decisiones.md`: bloqueo por email, sesión deslizante.
- **Tests**: `npm run check` (60 pytest, 26 vitest, eslint, ruff, tsc, mypy estricto, build, patrones prohibidos) y `verify-e0` 26/26 con capturas.

## Trabajo directo en `main` (13/11/2026)

- **Qué**: PR #1 fusionado y rama `feature/e0-andamiaje` borrada; desde ahora CC hace commit y push a `main` sin ramas ni PR. Registrado como D6 en `docs/decisiones.md`; reglas de cierre del `CLAUDE.md` actualizadas ("check en verde → commit → push a main").
- **Por qué**: decisión de Juanma; la protección es `npm run check` en verde antes de cada push y el CI en cada push.
- **Tests**: `npm run check` en verde antes del push; CI del push a `main`.
