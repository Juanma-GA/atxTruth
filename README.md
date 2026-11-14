# atxTruth

La *source of truth* de Customer Services de ATEXIS/ALTEN: catálogo de servicios y referencias de
proyecto en PostgreSQL, y generación **determinista** (sin IA) de PowerPoint, HTML, Markdown y Excel.

Estado: **E0 — andamiaje**. Hay login con roles, ajustes editables, auditoría, interfaz en EN/ES/FR y
el aspecto del mockup. Las referencias y el catálogo llegan en los encargos siguientes
([plan general](docs/plan/00-plan-general.md)).

- Stack: React 18 + TypeScript + Vite + Tailwind 4 + shadcn/ui · FastAPI + SQLAlchemy async + Alembic · PostgreSQL 16.
- Marco: [AACF](aacf/AGENTS.md) (versión en `aacf/VERSION`). Desviaciones decididas: [docs/decisiones.md](docs/decisiones.md).
- Contexto para agentes: [CLAUDE.md](CLAUDE.md).

## Requisitos

- Node.js 22 y npm.
- Python 3.12 o 3.13 (los lockfiles valen para las dos, en Windows y en Linux; el CI prueba ambas).
- PostgreSQL 16: con Docker (`docker compose up -d db`) o instalado en la máquina.

## Arrancar en local

Los comandos son los mismos en Linux y en Windows (PowerShell) salvo donde se indica.

### 1. Base de datos

```bash
docker compose up -d db
```

Sin Docker, crea en tu Postgres 16 un rol `atxtruth` con contraseña `atxtruth_dev`, permiso `CREATEDB`
y una base `atxtruth` suya (o cambia `DATABASE_URL` en `backend/.env`).

### 2. Backend

Linux / macOS (con `python3.12` o `python3.13`, la que tengas):

```bash
cd backend
python3.13 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements-dev.lock.txt
cp .env.example .env
.venv/bin/python scripts/generate_jwt_keys.py
.venv/bin/alembic upgrade head
```

Windows (PowerShell). Con el lanzador `py`, elige la versión (`py -3.13` o `py -3.12`); si no tienes
`py` (por ejemplo, Python de la Microsoft Store), usa `python -m venv .venv` y comprueba antes con
`python --version` que es 3.12 o 3.13:

```powershell
cd backend
py -3.13 -m venv .venv          # o: py -3.12 -m venv .venv   ·   sin lanzador: python -m venv .venv
.venv\Scripts\pip install --require-hashes -r requirements-dev.lock.txt
Copy-Item .env.example .env
.venv\Scripts\python scripts\generate_jwt_keys.py
.venv\Scripts\alembic upgrade head
```

Admin inicial (y, solo en desarrollo, un editor y un viewer de ejemplo):

```bash
INITIAL_ADMIN_EMAIL=admin@example.com INITIAL_ADMIN_PASSWORD='elige-una-de-12+' .venv/bin/python scripts/create_admin_user.py
DEV_SEED_PASSWORD='elige-otra-de-12+' .venv/bin/python scripts/seed_dev_data.py
```

```powershell
$env:INITIAL_ADMIN_EMAIL="admin@example.com"; $env:INITIAL_ADMIN_PASSWORD="elige-una-de-12+"
.venv\Scripts\python scripts\create_admin_user.py
$env:DEV_SEED_PASSWORD="elige-otra-de-12+"; .venv\Scripts\python scripts\seed_dev_data.py
```

### 3. Frontend y herramientas de raíz

```bash
npm ci
npm ci --prefix frontend
```

### 4. Arrancar

En dos terminales, desde la raíz:

```bash
npm run dev:backend
```

```bash
npm run dev:frontend
```

Abre <http://localhost:5173>. La API (OpenAPI en <http://localhost:8000/api/docs>) se sirve por el proxy de Vite en `/api`.

## Verificar

```bash
npm run test:db:create
npm run check
```

- `npm run test:db:create` crea y migra la base de tests (`atxtruth_test`), una sola vez y tras cada migración nueva.
- `npm run check` pasa lint, tipos, build y tests; `npm run check -- --keep-going` sigue tras un fallo. Sale con 0 (bien), 1 (algo falla) o 2 (falta algo del entorno, y dice qué).
- `npm run verify:e0` (con backend y frontend arrancados y `VERIFY_ADMIN_EMAIL` / `VERIFY_ADMIN_PASSWORD`) prueba la app en Chromium y deja capturas en `artifacts/verify-e0/`. La primera vez en una máquina nueva: `npx playwright install chromium`.

## Producción

Lo despliega IT (encargo F1). Lo que la app ya deja preparado:

- `AUTH_MODE=oidc` para SSO/MFA: qué hay que implementar en [docs/sso-para-it.md](docs/sso-para-it.md).
- `ENVIRONMENT=production` activa HSTS; `COOKIE_SECURE=true` exige HTTPS.
- El frontend se compila con `npm --prefix frontend run build` (`frontend/dist/`). El servidor web que lo sirva debe enviar la misma CSP que `vite preview` (`frontend/vite.config.ts`) y pasar `/api` al backend.
- Postgres es la única fuente de verdad; los secretos van solo por entorno.

## Red corporativa con inspección SSL

Si `npm ci` o `pip` fallan con errores de certificado detrás del proxy corporativo, pide a IT el
certificado raíz y configúralo (`npm config set cafile ruta\al\ca.pem`, `PIP_CERT=ruta\al\ca.pem`).
No desactives la verificación SSL.
