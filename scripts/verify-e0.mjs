#!/usr/bin/env node
// E0 end-to-end check in a real Chromium against the running frontend + backend.
//   Needs: backend (npm run dev:backend) and frontend (npm run dev:frontend) running, and the
//   seeded admin in VERIFY_ADMIN_EMAIL / VERIFY_ADMIN_PASSWORD (or INITIAL_ADMIN_EMAIL / _PASSWORD).
//   ATX_WEB_URL (default http://localhost:5173) points at the frontend; the API goes through its proxy.
// Leaves the database as it was: restores the admin's language/theme and the setting it changes,
// and deletes the users it creates (the audit trail keeps their events, by design).
// Screenshots: artifacts/verify-e0/. Exit codes: 0 ok, 1 a check failed, 2 environment missing.
import { mkdirSync } from 'node:fs';
import path from 'node:path';

import AxeBuilder from '@axe-core/playwright';
import { chromium } from 'playwright';

import { apiClient } from './lib/api.mjs';
import { ARTIFACTS } from './lib/paths.mjs';

const WEB = (process.env.ATX_WEB_URL ?? 'http://localhost:5173').replace(/\/$/, '');
const ADMIN_EMAIL = process.env.VERIFY_ADMIN_EMAIL ?? process.env.INITIAL_ADMIN_EMAIL;
const ADMIN_PASSWORD = process.env.VERIFY_ADMIN_PASSWORD ?? process.env.INITIAL_ADMIN_PASSWORD;
const SHOTS = path.join(ARTIFACTS, 'verify-e0');
const RUN = Date.now().toString(36);
const NEW_PASSWORD = `Verify-${RUN}-Pass!9`; // pragma: allowlist secret
const PAGE_SIZE_KEY = 'ui.table_page_size';

const results = [];
function check(name, ok, detail = '') {
  results.push({ name, ok });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) throw new Error(`check failed: ${name}`);
}

if (!ADMIN_EMAIL || !ADMIN_PASSWORD) {
  console.error('Set VERIFY_ADMIN_EMAIL and VERIFY_ADMIN_PASSWORD (or INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD).');
  process.exit(2);
}
const api = apiClient(WEB);
try {
  const health = await api.call('GET', '/api/health');
  if (health.status !== 200) throw new Error(String(health.status));
} catch (error) {
  console.error(`The app is not reachable at ${WEB} (frontend + backend running?): ${error.message}`);
  process.exit(2);
}

mkdirSync(SHOTS, { recursive: true });
const shot = (page, name) => page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });

async function axe(page, name) {
  const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  const serious = violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
  check(`a11y (axe WCAG 2.2 AA) — ${name}`, serious.length === 0, serious.map((v) => `${v.id}: ${v.nodes.length}`).join(', '));
}

const isMePatch = (r) => r.url().endsWith('/api/auth/me') && r.request().method() === 'PATCH';

/** Clicks and waits for the background PATCH /api/auth/me the optimistic UI sends. */
async function clickAndWaitForMePatch(page, locator, beforeWait) {
  const saved = page.waitForResponse(isMePatch);
  await locator.click();
  if (beforeWait) await beforeWait();
  return saved;
}

async function uiLogin(page, email, password) {
  await page.goto(`${WEB}/login`);
  await page.locator('#login-email').fill(email);
  await page.locator('#login-password').fill(password);
  await page.locator('form button[type=submit]').click();
}

const adminToken = await api.login(ADMIN_EMAIL, ADMIN_PASSWORD);
const me = (await api.call('GET', '/api/auth/me', { token: adminToken })).json;
const original = {
  language: me.preferred_language,
  theme: me.theme,
  pageSize: (await api.call('GET', '/api/settings', { token: adminToken })).json.find((s) => s.key === PAGE_SIZE_KEY).value,
};
const createdUsers = [];
const browser = await chromium.launch();
let exitCode = 0;

try {
  // Start from a known state: EN, theme follows the system.
  await api.call('PATCH', '/api/auth/me', { token: adminToken, body: { preferred_language: 'en', theme: 'system' } });

  // ── 1. Login + shell, light and dark ──────────────────────────────────────────────
  const context = await browser.newContext({ viewport: { width: 1366, height: 860 }, colorScheme: 'light' });
  const page = await context.newPage();
  await uiLogin(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.getByRole('navigation', { name: 'Main navigation' }).waitFor();
  check('admin signs in and sees the shell', await page.getByRole('link', { name: 'Home', exact: true }).isVisible());
  check('ALTEN logo in the top bar', await page.getByRole('img', { name: 'ALTEN' }).isVisible());
  const railLinks = await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link').allTextContents();
  check('rail shows only what exists (Home, Settings)', JSON.stringify(railLinks) === JSON.stringify(['Home', 'Settings']), railLinks.join(', '));
  await shot(page, 'shell-light');
  await axe(page, 'home light');

  await clickAndWaitForMePatch(page, page.getByRole('button', { name: 'Dark' }), async () => {
    const darkApplied = await page
      .waitForFunction(() => document.documentElement.dataset.theme === 'dark', null, { timeout: 1000 })
      .then(() => true, () => false);
    check('dark theme applied at once (optimistic)', darkApplied);
  });
  await shot(page, 'shell-dark');
  await axe(page, 'home dark');
  const storedTheme = (await api.call('GET', '/api/auth/me', { token: adminToken })).json.theme;
  check('theme stored in the account (Postgres)', storedTheme === 'dark', storedTheme);
  await clickAndWaitForMePatch(page, page.getByRole('button', { name: 'System' }));

  // ── 2. Language EN/ES/FR, kept after signing out and in again ─────────────────────
  await clickAndWaitForMePatch(page, page.getByRole('button', { name: 'Spanish' }), async () => {
    await page.getByRole('link', { name: 'Inicio', exact: true }).waitFor();
    check('switching to ES changes the interface', await page.getByRole('link', { name: 'Ajustes', exact: true }).isVisible());
  });
  await page.getByRole('button', { name: 'Menú de usuario' }).click();
  await page.getByRole('menuitem', { name: 'Cerrar sesión' }).click();
  await page.locator('#login-email').waitFor();
  await uiLogin(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.getByRole('link', { name: 'Inicio', exact: true }).waitFor();
  check('language kept after signing out and in (stored in Postgres)', (await page.locator('html').getAttribute('lang')) === 'es');

  for (const [lang, button, tab] of [
    ['es', 'Español', 'Configuración'],
    ['fr', 'Francés', 'Configuration'],
    ['en', 'Anglais', 'Configuration'],
  ]) {
    if (lang !== 'es') await clickAndWaitForMePatch(page, page.getByRole('button', { name: button }));
    await page.goto(`${WEB}/settings/configuration`);
    await page.locator(`[data-setting="${PAGE_SIZE_KEY}"]`).waitFor();
    check(`settings page in ${lang.toUpperCase()}`, (await page.locator('html').getAttribute('lang')) === lang && (await page.getByRole('link', { name: tab, exact: true }).isVisible()));
    await shot(page, `settings-${lang}`);
  }
  await axe(page, 'configuration');

  // ── 3. Change a setting: optimistic, survives a reload, appears in the audit trail ──
  const newSize = original.pageSize === 37 ? 38 : 37;
  const input = page.locator(`[data-setting="${PAGE_SIZE_KEY}"] input`);
  await input.fill(String(newSize));
  const patchDone = page.waitForResponse((r) => r.url().includes(`/api/settings/${PAGE_SIZE_KEY}`) && r.request().method() === 'PATCH');
  await input.press('Enter');
  check('setting shows the new value at once (optimistic)', (await input.inputValue()) === String(newSize));
  check('server accepted the change', (await patchDone).status() === 200);
  await page.reload();
  await page.locator(`[data-setting="${PAGE_SIZE_KEY}"] input`).waitFor();
  check('setting survives a reload', (await page.locator(`[data-setting="${PAGE_SIZE_KEY}"] input`).inputValue()) === String(newSize));
  await page.goto(`${WEB}/settings/audit`);
  const auditRow = page.locator('tr[data-action="settings.updated"]').first();
  await auditRow.waitFor();
  const auditText = await auditRow.textContent();
  check('change recorded in the audit trail', auditText.includes(String(newSize)) && auditText.includes(ADMIN_EMAIL), auditText);
  await shot(page, 'audit');

  const bad = await api.call('PATCH', `/api/settings/${PAGE_SIZE_KEY}`, { token: adminToken, body: { value: 100000 } });
  check('server rejects an out-of-range value with a code', bad.status === 422 && bad.json.error.code === 'settings.too_large');

  // ── 4. Viewer: no Configuration tab, 403 from the API ─────────────────────────────
  const viewerEmail = `verify-viewer-${RUN}@example.com`;
  const createdViewer = await api.call('POST', '/api/users', {
    token: adminToken,
    body: { email: viewerEmail, display_name: 'Verify Viewer', role: 'viewer' },
  });
  check('admin creates a viewer through the API', createdViewer.status === 201);
  createdUsers.push(createdViewer.json.user.id);
  const viewerTemp = await api.login(viewerEmail, createdViewer.json.temporary_password);
  await api.call('POST', '/api/auth/change-password', {
    token: viewerTemp,
    body: { current_password: createdViewer.json.temporary_password, new_password: NEW_PASSWORD },
  });
  const viewerToken = await api.login(viewerEmail, NEW_PASSWORD);
  const viewerSettings = await api.call('GET', '/api/settings', { token: viewerToken });
  const viewerPatch = await api.call('PATCH', `/api/settings/${PAGE_SIZE_KEY}`, { token: viewerToken, body: { value: 10 } });
  check('viewer gets 403 from the settings API', viewerSettings.status === 403 && viewerPatch.status === 403);
  const viewerContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const viewerPage = await viewerContext.newPage();
  await uiLogin(viewerPage, viewerEmail, NEW_PASSWORD);
  await viewerPage.getByRole('navigation', { name: 'Main navigation' }).waitFor();
  await viewerPage.goto(`${WEB}/settings/configuration`);
  await viewerPage.getByRole('link', { name: 'My account', exact: true }).waitFor();
  await viewerPage.waitForURL('**/settings/account');
  check('viewer does not see the Configuration screen', (await viewerPage.getByRole('link', { name: 'Configuration', exact: true }).count()) === 0, viewerPage.url());
  await viewerContext.close();

  // ── 5. Admin creates an editor in the UI; the editor must change the temporary password ──
  const editorEmail = `verify-editor-${RUN}@example.com`;
  await page.goto(`${WEB}/settings/users`);
  await page.getByRole('button', { name: 'New user' }).click();
  await page.locator('#nu-email').fill(editorEmail);
  await page.locator('#nu-name').fill('Verify Editor');
  await page.locator('#nu-role').selectOption('editor');
  const created = page.waitForResponse((r) => r.url().endsWith('/api/users') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Create user' }).click();
  const createdJson = await (await created).json();
  createdUsers.push(createdJson.user.id);
  const temporary = (await page.getByTestId('temporary-password').textContent()).trim();
  check('temporary password shown once to the admin', temporary.length >= 12 && temporary === createdJson.temporary_password);
  await shot(page, 'users-temporary-password');
  await page.getByRole('button', { name: 'Close' }).first().click();
  await page.locator(`tr[data-user="${editorEmail}"]`).waitFor();
  check('new editor listed with a pending password change', (await page.locator(`tr[data-user="${editorEmail}"]`).textContent()).includes('Must change password'));

  const editorContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const editorPage = await editorContext.newPage();
  await uiLogin(editorPage, editorEmail, temporary);
  await editorPage.locator('#pw-current').waitFor();
  check('editor is forced to change the password', (await editorPage.getByRole('navigation', { name: 'Main navigation' }).count()) === 0);
  await editorPage.locator('#pw-current').fill(temporary);
  await editorPage.locator('#pw-new').fill(NEW_PASSWORD);
  await editorPage.locator('#pw-confirm').fill(NEW_PASSWORD);
  await editorPage.getByRole('button', { name: 'Change password' }).click();
  await editorPage.getByRole('navigation', { name: 'Main navigation' }).waitFor();
  check('after changing it the editor gets in', await editorPage.getByRole('link', { name: 'Home', exact: true }).isVisible());
  await editorContext.close();

  // ── 6. Mobile width: no horizontal scroll ─────────────────────────────────────────
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${WEB}/settings/configuration`);
  await page.locator(`[data-setting="${PAGE_SIZE_KEY}"]`).waitFor();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  check('usable at phone width (no horizontal scroll)', overflow <= 0, `${overflow}px`);
  await shot(page, 'settings-mobile');
  await context.close();
} catch (error) {
  exitCode = 1;
  console.error(error);
} finally {
  // Leave the database as it was.
  await api.call('PATCH', `/api/settings/${PAGE_SIZE_KEY}`, { token: adminToken, body: { value: original.pageSize } });
  await api.call('PATCH', '/api/auth/me', {
    token: adminToken,
    body: { preferred_language: original.language, theme: original.theme },
  });
  for (const id of createdUsers) {
    const user = (await api.call('POST', `/api/users/${id}/deactivate`, { token: adminToken })).json;
    if (user?.email) await api.call('POST', `/api/users/${id}/delete-permanently`, { token: adminToken, body: { confirm_email: user.email } });
  }
  await browser.close();
}

const failed = results.filter((r) => !r.ok).length;
console.log(`\nverify-e0: ${results.length - failed}/${results.length} checks passed${exitCode ? ' (stopped at a failure)' : ''}. Screenshots in artifacts/verify-e0/`);
process.exit(exitCode);
