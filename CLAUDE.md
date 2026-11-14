# CLAUDE.md — Contexto de atxTruth para Claude Code

atxTruth es la *source of truth* de Customer Services de ATEXIS/ALTEN: catálogo de servicios y
referencias de proyecto en Postgres, con generación determinista (sin IA) de PPTX, HTML, Markdown y
Excel. Plan completo: [`docs/plan/00-plan-general.md`](docs/plan/00-plan-general.md).

## ⚠️ El AACF tiene prioridad sobre este fichero

- Este proyecto sigue el **ATEXIS AI-Assisted Coding Framework** copiado sin cambios en `aacf/` (versión `aacf/VERSION` = 2.0.0, de `Juanma-GA/aacf`, rama `claude/crear-carpetas-en-sp-e57wrh`). **Si el AACF y este fichero chocan, gana el AACF** y este fichero se corrige.
- Antes de dar algo por terminado, autocomprobar **HR0–HR21** (`aacf/rules/atexis-hard-rules.md`). Las más relevantes aquí: HR0/HR8 (nada fijo en código; cada ajuste funcional tiene su sitio en Ajustes → Configuración), HR1 (nunca `localStorage`/`sessionStorage`), HR7 (nada de vueltas atrás silenciosas), HR9 (borrado lógico; el definitivo, confirmado y auditado), HR10 (mezcla profunda), HR15/HR21 (todo texto visible por i18n y humanizado), HR20 (UI optimista).
- El MCP `aacf_fetch` solo está en la red corporativa: desde el entorno remoto no se alcanza, así que se usa la copia local y **hay que decirlo en el informe** (puede estar desactualizada). No mezclar ficheros de versiones distintas; `aacf/` no se toca.
- Desviaciones decididas (D1–D6) y decisiones técnicas: [`docs/decisiones.md`](docs/decisiones.md). Una desviación nueva se anota ahí con fecha.
- Revisión: el agente `aacf/agents/code-reviewer.agent.md` en contexto aislado revisa los cambios de cada encargo antes del push.

## Cómo levantar el entorno

Detalle para Linux y Windows en el [README](README.md). Resumen:

```bash
docker compose up -d db                       # o un Postgres 16 local (en el entorno remoto: service postgresql start)
cd backend && .venv/bin/alembic upgrade head  # migraciones
npm run dev:backend                           # uvicorn :8000 (sin --reload: reiniciar tras cambiar Python)
npm run dev:frontend                          # vite :5173, proxy /api → :8000
```

- Backend: dependencias fijadas con hashes (`backend/requirements[-dev].lock.txt`, de `pyproject.toml` con `uv pip compile --universal --generate-hashes --python-version 3.12`; valen para Python 3.12 y 3.13, en Linux y Windows, y el CI prueba las dos versiones). Frontend y raíz: `npm ci` con `package-lock.json`. Antes de añadir un paquete, comprobar que existe, está mantenido y tiene ≥30 días (`npm install --before=…`, `uv … --exclude-newer …`).
- Claves JWT en `backend/keys/` (no en git): `python scripts/generate_jwt_keys.py`.
- Usuarios de desarrollo: admin con `scripts/create_admin_user.py` (`INITIAL_ADMIN_EMAIL`/`INITIAL_ADMIN_PASSWORD`); editor y viewer de ejemplo con `scripts/seed_dev_data.py` (`DEV_SEED_PASSWORD`). Datos siempre sintéticos.

## Cómo verificar

- **`npm run check`** (raíz, scripts de Node: igual en Linux y PowerShell): patrones prohibidos → secretos (detect-secrets) → tokens → eslint → ruff (check + format) → tsc → mypy estricto (`app/`) → vite build → vitest → base de tests → pytest. Para en el primer fallo; `-- --keep-going` sigue y lista todos. Salida: 0 bien, 1 algo falla, 2 falta algo del entorno (dice qué). El resumen dice qué Python usó.
- **Tests de backend**: Postgres real, sin mocks de la base, en su **propia base** `TEST_DATABASE_URL` (nombre acabado en `_test`, nunca la de la app; lo impone `backend/tests/conftest.py` con las reglas de `backend/tests/_testdb.py`). `npm run test:db:create` la crea y migra (repetir tras cada migración nueva).
- **Navegador**: `scripts/verify-<encargo>.mjs` con Playwright contra backend y frontend arrancados (`VERIFY_ADMIN_EMAIL`/`VERIFY_ADMIN_PASSWORD`). Cada `verify-*` deja la base como estaba (restaura ajustes e idioma/tema, borra los usuarios que crea; la auditoría conserva sus eventos). Tras una acción optimista, esperar la respuesta del servidor (`waitForResponse`) antes de comprobar por la API. Capturas en `artifacts/` (no se versiona).
- **Pre-commit** (`pre-commit install`): detect-secrets (baseline `.secrets.baseline`), patrones prohibidos, ruff, eslint. **CI** (`.github/workflows/ci.yml`): escaneo de secretos + `npm run check` con un servicio Postgres.
- **Windows**: nada de rutas `/tmp`, `.venv/bin` fijo, `shell: true` ni programas que Windows no tenga en `scripts/` (lo vigila `check-forbidden.mjs`); todo fichero de texto en Python se abre con `encoding=` (test `test_text_files_opened_with_explicit_encoding`); `.gitattributes` fija LF.

## Reglas de cierre de cada encargo

1. Siempre `npm run check`, y el orden es: **check en verde → commit → push a `main`** (sin ramas ni PR, desviación D6). Después del push, vigilar el CI y arreglarlo si falla.
2. Navegador: el `verify-*` nuevo del encargo y, como mucho, los dos o tres que cubren las pantallas que cambia.
3. Si un script antiguo falla, ejecútalo una vez sobre el commit anterior: si allí también falla, va al informe y no se arregla en el encargo; si allí pasaba, es una regresión y se arregla.
4. **Informe**: qué se hizo, qué no y por qué, desviaciones del AACF nuevas (si las hay) y el resumen final de `check` tal cual. Sin repetir lo que ya cuentan los commits.
5. Si el encargo va a pasar de dos partes grandes o el contexto se va a resumir a mitad, avisa al terminar la primera parte y entrega por partes.
6. Una entrada en `docs/historial-cambios.md` (corta: qué, por qué, commit y tests).

Se trabaja directamente en `main` (desviación D6 de AACF G5): nunca se hace push sin `npm run check` en verde, y el CI corre en cada push.

## Convenciones del proyecto (se aplican desde E1)

1. **Ajustes funcionales en la UI de administración (HR0/HR8).** Tabla `app_settings` (clave, valor JSONB, tipo, restricciones, etiqueta y descripción traducibles), pantalla Ajustes → Configuración solo para admin, validación por tipo (`backend/app/services/settings.py`), mezcla profunda para objetos (HR10) y auditoría de cada cambio. Un ajuste nuevo entra por **migración** (fila completa con sus tres idiomas) y se lee con `get_values()`, que falla en alto si falta. Secretos e infraestructura (`DATABASE_URL`, claves JWT, CORS…) solo por entorno, mostrados en solo lectura y enmascarados.
2. **Identificadores estables.** Toda entidad de negocio tiene un código legible y estable (`REF-0049`, `S2.1.3`) además del UUID. Importaciones y exportaciones se casan por el código.
3. **Borrado lógico** en todo (`deleted_at`, `deleted_by`) con papelera para restaurar. El borrado definitivo pide confirmación explícita (escribir el identificador) y queda auditado (HR9).
4. **UI optimista** en toda edición (HR20): se refleja al momento, se guarda en segundo plano y, si el servidor rechaza, vuelve atrás y dice por qué (patrón: `onMutate`/`onError` de TanStack Query, ver `frontend/src/hooks/useUsers.ts`). Excepciones solo con resultado generado por el servidor, comentadas en el código.
5. **Excel de ida y vuelta**: toda entidad gestionada se exporta a `.xlsx` y se reimporta con cambios. Formato estable con hoja `_meta` (versión del formato, fecha, edición de catálogo); una columna por idioma en los campos traducibles (`Title [EN]`, `Title [ES]`, `Title [FR]`); importación en dos fases (Analizar → informe de altas, cambios, bajas y errores fila a fila; Aplicar en una transacción), idempotente por código estable y que **nunca borra por omisión**. Infraestructura común en E1.
6. **Listas de valores editables**: sectores, estados de revisión, modelos de entrega… son datos que un admin crea y modifica, no constantes de código (E1).
7. **Generación determinista**: misma entrada, mismo fichero; tests contra ficheros de referencia (E4).
8. **Contenido traducible**: los textos de negocio que se publican son `TranslatableText` — JSONB `{"en", "es", "fr"}`. EN es maestro y obligatorio; ES y FR opcionales. Backend: `app/schemas/translatable.py` (`TranslatableText`, columna `TranslatableTextType`). Frontend: `src/types/translatable.ts`, `TranslatedText` (muestra el idioma de la interfaz y, si falta, el EN **con el aviso** "Sin traducción al FR"; nunca inglés sin avisar, HR7) y `TranslatableTextEditor` (pestañas EN/ES/FR con marca de traducción que falta).
9. **Errores**: el backend responde `{"error": {"code", "params"}}` (`AppError`); el frontend traduce `errors.<code>` (`services/apiErrors.ts`). Nunca un texto del servidor ni un token crudo en pantalla. Un código nuevo se añade en los tres idiomas (el test de i18n lo exige).
10. **Capas del backend**: rutas finas en `app/api/routes/`; lógica en `app/services/`; acceso a datos **solo** en `app/repositories/`. Nunca `from __future__ import annotations` en rutas. Pydantic de entrada con `extra="forbid"` (`StrictModel`).
11. **Diseño**: colores, tipografías, radios y medidas salen de `frontend/design.tokens.json` (DTCG, OKLCH) compilado por Style Dictionary a variables CSS y al tema de Tailwind (sin paleta por defecto). Ningún componente escribe un color a mano. Componentes shadcn en `src/components/ui/`.
12. **Roles**: `admin`, `editor`, `viewer`, comprobados en el servidor en cada endpoint (`require_roles`, `require_admin`, `require_editor` en `app/auth/deps.py`). La UI solo oculta; la API decide.

## Ficheros clave

| Fichero | Para qué |
|---|---|
| `backend/app/main.py` | App FastAPI: middlewares, errores, routers (los de login local y usuarios solo con `AUTH_MODE=local`) |
| `backend/app/core/config.py` | Configuración de infraestructura (solo entorno) |
| `backend/app/core/security.py` | bcrypt, contraseñas temporales, JWT RS256, refresh tokens |
| `backend/app/core/errors.py`, `middleware.py`, `logging.py` | Contrato de errores, cabeceras de seguridad (CSP), logs JSON |
| `backend/app/auth/` | `AuthProvider` (local / enganche OIDC), `CurrentUser`, dependencias de rol |
| `backend/app/services/{auth,users,settings,audit}.py` | Lógica de negocio |
| `backend/app/repositories/` | Único acceso a datos |
| `backend/alembic/versions/0001_base.py` | Tablas base y siembra de ajustes |
| `backend/tests/conftest.py`, `_testdb.py` | Base de tests propia, migrada y limpia por test |
| `frontend/design.tokens.json`, `style-dictionary.config.mjs` | Tokens → `src/styles/generated/tokens.css` (generado, no se versiona) |
| `frontend/src/App.tsx` | Arranque de sesión, idioma/tema, rutas |
| `frontend/src/components/layout/AppShell.tsx` | Shell: barra superior, raíl, zona de trabajo |
| `frontend/src/services/api.ts`, `apiErrors.ts` | Cliente API (token en memoria, refresh por cookie) y traducción de errores |
| `frontend/src/i18n/locales/{en,es,fr}.json` | Textos de la interfaz |
| `frontend/src/pages/settings/` | Mi cuenta, Configuración, Usuarios, Auditoría |
| `scripts/check.mjs`, `check-forbidden.mjs`, `verify-e0.mjs` | Verificación |
| `docs/decisiones.md`, `docs/sso-para-it.md`, `docs/historial-cambios.md` | Decisiones, traspaso de SSO a IT, historial |

## Lo que NO está implementado todavía

- Ninguna entidad de negocio: taxonomía, listas de valores, referencias, catálogo, plantillas, generadores, importación/exportación de Excel (E1–E9).
- OIDC/SSO real y MFA (lo hace IT; ver `docs/sso-para-it.md`), despliegue en el servidor de IT y controles de datos confidenciales (F1, D4).
- Papelera genérica (solo existe la desactivación/reactivación de usuarios).
- Storybook del design system.
- Cualquier llamada a un LLM o el servidor MCP (F2).
