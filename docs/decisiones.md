# Decisiones y desviaciones del AACF

Registro de decisiones que se apartan del AACF (versión local 2.0.0) o que lo concretan, para que un
revisor no las tome por fallos. Fecha de las decisiones D1–D5: **13/11/2026** (Juanma).

## Desviaciones decididas por Juanma

| # | Desviación | Decisión |
|---|---|---|
| D1 | `styles/branding.md` pide azul ATEXIS `#2E74B5` + Inter | Se usa la paleta y la tipografía del mockup (`sources/design/mockup_look_and_feel.html`): navy `#173f7a`, IBM Plex. Siguen siendo tokens (Layer 1 del design system, `frontend/design.tokens.json`), así que cambiar de marca es tocar un fichero. |
| D2 | `security.mdc` pide Keycloak OIDC | Login local (JWT) en desarrollo, con la autorización desacoplada del login. SSO y MFA los implementa IT al desplegar; la app deja el punto de enganche preparado (`AuthProvider`, `AUTH_MODE`, [sso-para-it.md](sso-para-it.md)). |
| D3 | HR11 (LLM en vez de regex para decisiones semánticas) y HR6 (resumir con LLM) | No hay IA en la app hasta la fase MCP. Lo que el código pueda comprobar, lo comprueba el código. Nada se trunca: si algo no cabe, se avisa. |
| D4 | Clasificación de datos y nivel del AACF | Los datos de desarrollo son **sintéticos**. La clasificación real, el nivel (tier) y los controles de datos confidenciales los resuelve IT al desplegar en su servidor con datos reales. |
| D5 | Versión de la taxonomía | Las referencias se mapean al **Catálogo V0** (hoja `Lists` del Excel de referencias). El modelo admite varias ediciones, pero ahora solo se carga la V0. |

## Decisiones técnicas de E0 (13/11/2026)

- **Versión del AACF sin verificar.** El MCP `aacf_fetch` (`10.117.139.1`, red corporativa) no es alcanzable desde el entorno de desarrollo remoto: se trabaja con la copia local 2.0.0 de `Juanma-GA/aacf` (rama `claude/crear-carpetas-en-sp-e57wrh`, commit `d0ab40c`), copiada sin cambios en `aacf/`. Puede estar desactualizada; comprobar `aacf/VERSION` contra el MCP en cuanto haya acceso.
- **`aacf/` y `sources/` se guardan byte a byte** (`.gitattributes`: `-text`); el resto del repo, con LF.
- **Vite 6, Vitest 3, TypeScript 5.9, zod 4.** La plantilla del AACF pide Vite 6. TypeScript 7 (nativo) aún no lo soporta typescript-eslint. zod 4 porque zod 3 tiene un aviso de seguridad (GHSA-mrhx-c7xc-m3w5) sin parche en la rama 3.
- **Cuarentena de dependencias (G3)**: se instalaron con `npm install --before=2026-10-14` y `uv pip compile --exclude-newer 2026-10-14` (≥30 días de antigüedad). `npm audit --omit=dev`: 0 avisos. Quedan avisos moderados en herramientas de desarrollo (vitest/eslint transitivas); no se fuerzan saltos de versión mayor.
- **Access token RS256** con par de claves en `backend/keys/` (no se versiona; lo crea `scripts/generate_jwt_keys.py`). Validar con clave pública es el mismo esquema que validar un token del IdP por JWKS.
- **Refresh token**: cookie `HttpOnly; Secure; SameSite=Strict; Path=/api/auth`, rota en cada uso; reutilizar uno rotado fuera de un margen de 10 s cierra todas las sesiones del usuario. Además se comprueba `Origin` en los endpoints de cookie (CSRF).
- **Límite de intentos de login** contado sobre `audit_events` (fallos desde el último acceso correcto, dentro de la ventana): sin tabla nueva y válido con varios procesos. Umbral y ventana son un ajuste (`auth.login_rate_limit`).
- **Ajustes funcionales** en `app_settings`, sembrados en la migración `0001` (tipo, restricciones, valor por defecto, etiqueta y descripción traducibles). Además de los cinco pedidos, se añadieron `auth.login_rate_limit` (objeto, ejercita la mezcla profunda) y `auth.password_min_length` (HR8: umbrales configurables).
- **`preferred_language` nulo** = la cuenta sigue el idioma por defecto del ajuste `i18n.default_language`.
- **Excepciones a HR20 (UI optimista)**, documentadas en el código: crear usuario y restablecer contraseña (el id y la contraseña temporal los genera el servidor) y cambiar contraseña (depende de que el servidor compruebe la actual).
- **CSP de producción** con `style-src 'unsafe-inline'`: sonner y Radix insertan estilos en tiempo de ejecución. Los scripts siguen limitados a `'self'`.
- **Storybook** (contrato visual del design system) no se monta en E0; la comprobación de accesibilidad (axe, WCAG 2.2 AA) va en `verify-e0`.
