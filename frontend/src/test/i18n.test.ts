import { describe, expect, it } from 'vitest';

import en from '@/i18n/locales/en.json';
import es from '@/i18n/locales/es.json';
import fr from '@/i18n/locales/fr.json';

function leaves(obj: unknown, prefix = ''): Map<string, string> {
  const out = new Map<string, string>();
  if (obj && typeof obj === 'object') {
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      const path = prefix ? `${prefix}.${key}` : key;
      if (typeof value === 'string') out.set(path, value);
      else for (const [k, v] of leaves(value, path)) out.set(k, v);
    }
  }
  return out;
}

const locales = { en: leaves(en), es: leaves(es), fr: leaves(fr) };

describe('translations (HR15)', () => {
  it.each(['es', 'fr'] as const)('%s has exactly the same keys as en', (lang) => {
    const missing = [...locales.en.keys()].filter((k) => !locales[lang].has(k));
    const extra = [...locales[lang].keys()].filter((k) => !locales.en.has(k));
    expect({ missing, extra }).toEqual({ missing: [], extra: [] });
  });

  it.each(['en', 'es', 'fr'] as const)('%s has no empty strings', (lang) => {
    expect([...locales[lang].entries()].filter(([, v]) => v.trim() === '').map(([k]) => k)).toEqual([]);
  });

  it.each(['es', 'fr'] as const)('%s uses the same interpolation variables as en', (lang) => {
    const vars = (s: string) => [...s.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]).sort();
    const mismatched = [...locales.en.entries()]
      .filter(([k, v]) => JSON.stringify(vars(v)) !== JSON.stringify(vars(locales[lang].get(k) ?? '')))
      .map(([k]) => k);
    expect(mismatched).toEqual([]);
  });

  it('translates every backend error code the API can return', () => {
    // Codes raised in backend/app (AppError(...)) — kept in sync by this list and the backend test suite.
    const codes = [
      'auth.invalid_credentials', 'auth.too_many_attempts', 'auth.session_expired', 'auth.not_authenticated',
      'auth.forbidden', 'auth.password_change_required', 'auth.current_password_incorrect',
      'auth.password_too_short', 'auth.password_too_long', 'auth.password_unchanged', 'auth.origin_not_allowed',
      'users.not_found', 'users.email_taken', 'users.last_admin', 'users.cannot_change_own_role',
      'users.cannot_deactivate_self', 'users.inactive', 'users.must_deactivate_first', 'users.confirmation_mismatch',
      'settings.not_found', 'settings.invalid_type', 'settings.too_small', 'settings.too_large', 'settings.too_short',
      'settings.too_long', 'settings.invalid_option', 'settings.unknown_field', 'settings.missing_field',
      'settings.unsupported_type', 'validation.failed', 'server.internal',
    ];
    expect(codes.filter((c) => !locales.en.has(`errors.${c}`))).toEqual([]);
  });
});
