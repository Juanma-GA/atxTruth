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

## Python 3.13 en el CI (14/11/2026)

- **Qué**: matriz del CI con Python 3.12 y 3.13 (`.github/workflows/ci.yml`, `fail-fast: false`); el README dice que vale 3.12 o 3.13, con `python -m venv .venv` cuando en Windows no hay lanzador `py`.
- **Por qué**: Juanma desarrolla en Windows con Python 3.13.
- **Comprobado**: los lockfiles no cambian: `pip download --require-hashes --platform win_amd64 --python-version 3.13 --only-binary=:all:` resuelve los dos (`requirements.lock.txt` y `requirements-dev.lock.txt`), y con 3.13 en Linux pasan los 60 tests de pytest y mypy estricto.
- **Tests**: `npm run check` en verde; CI del push con las dos versiones.

## E1 — parte 1: arreglos previos, listas, Excel de ida y vuelta y carga inicial (14/11/2026)

- **Qué**:
  - Arreglos previos, cada uno en su commit: favicons cuadrados con el símbolo de ALTEN (`scripts/generate_favicons.py`, `3d5c7bd`); vitest 4 y style-dictionary 5, sin avisos críticos ni altos (`d313c63`); escaneo de secretos que solo falla por secretos nuevos (`39e7783`).
  - Listas de valores: modelo, API y UI con reordenación, activo, papelera y permisos.
  - Taxonomía V0 en el backend: modelo, API, borrado protegido, cambio de código confirmado e historial.
  - Motor genérico de Excel de ida y vuelta.
  - Adaptador de la hoja Lists (UI en Ajustes → Datos iniciales y script).
  - `FieldState`, y origen de cada cambio (App o Excel con el nombre del fichero) en la auditoría.
- **Por qué**: encargo E1. Se entrega por partes; la parte 2 trae la UI del catálogo, el borrador de traducciones, `verify-e1` y la revisión.
- **Commits**: `fc41701` (backend) y el commit de esta entrada (frontend y documentación).
- **Tests**: `npm run check` en verde (pytest 101, vitest 28). Carga inicial: 7 listas (49 ítems), 6 bloques, 33 familias (1 propuesta), 86 servicios (3 propuestos), 8 soluciones, 7 adyacentes y 17 valores especiales; repetida, 0 cambios.
