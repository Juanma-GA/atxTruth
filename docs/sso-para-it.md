# SSO (OIDC) y MFA — qué tiene que implementar IT

La app arranca con `AUTH_MODE=local` (email + contraseña, para desarrollo). Para producción, IT conecta
el proveedor de identidad corporativo (Keycloak o Entra ID) con `AUTH_MODE=oidc`. La autorización no
cambia: todas las rutas dependen de un `CurrentUser` (id, email, nombre, roles), venga de donde venga.

Hoy, `AUTH_MODE=oidc` **hace fallar el arranque** con un mensaje que apunta aquí (no hay vuelta silenciosa al login local).

## Lo que hay que implementar

1. **`OidcAuthProvider`** en `backend/app/auth/provider.py`, subclase de `AuthProvider`, con `resolve(request, db) -> CurrentUser | None`:
   - leer el `Authorization: Bearer <token>` (`bearer_token()` ya existe);
   - validar firma, `iss`, `aud`, `exp` contra el JWKS del IdP (PyJWT ya está: `jwt.PyJWKClient`);
   - buscar el usuario por `external_subject` (= `sub` del token; la columna ya existe en `users`) o crearlo la primera vez (alta *just-in-time*), con email y nombre del token y `password_hash = NULL`;
   - **mapear grupos a roles**: grupo del IdP → `admin` / `editor` / `viewer`. El mapeo debe ser configuración (variable de entorno, p. ej. `OIDC_ROLE_MAP`), no código. Si un usuario no está en ningún grupo mapeado, no entra (`None` → 401); no se le da un rol por defecto;
   - actualizar `users.role` con el rol del token en cada acceso, para que la auditoría y la pantalla de ajustes lo reflejen.
2. **`build_auth_provider()`** (mismo fichero): devolver `OidcAuthProvider()` cuando `AUTH_MODE=oidc`.
3. **Configuración** en `backend/app/core/config.py`: `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_CLIENT_ID`, `OIDC_ROLE_MAP` y lo que pida el IdP; añadirlas (sin secretos visibles) a `infrastructure()` en `backend/app/services/settings.py` para que se vean en solo lectura en Ajustes → Configuración.
4. **Frontend**: en modo `oidc` la pantalla de login (`frontend/src/pages/LoginPage.tsx`) ya muestra solo el aviso; hay que añadir el flujo *Authorization Code + PKCE* (p. ej. `oidc-client-ts`) que obtenga el token y lo ponga en `useAuthStore.setSession()`, y la renovación silenciosa en `refreshSession()` (`frontend/src/services/api.ts`). Los tokens solo en memoria (HR1).
5. **MFA**: se exige en el IdP (política de Keycloak / acceso condicional de Entra ID). La app no implementa MFA propio.
6. **Cierre de sesión**: el menú de usuario llama a `/api/auth/logout`; en modo `oidc` debe redirigir al `end_session_endpoint` del IdP.

## Lo que no hace falta tocar

- Las comprobaciones de rol (`backend/app/auth/deps.py`: `require_roles`, `require_admin`, `require_editor`) y todas las rutas.
- La auditoría (`audit_events`) y el idioma y tema guardados en la cuenta.
- Las rutas de login local y de gestión de usuarios: con `AUTH_MODE=oidc` **no se montan** (`backend/app/main.py`) y la pestaña Usuarios se oculta en la interfaz.

## Pruebas que añadir

- Token válido de cada grupo → rol correcto; token caducado, con otra audiencia o sin grupo mapeado → 401.
- Alta *just-in-time* y actualización del rol en accesos posteriores.
- `/api/users` y `/api/auth/login` devuelven 404 en modo `oidc`.
