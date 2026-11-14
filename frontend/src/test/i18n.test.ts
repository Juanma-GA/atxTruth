import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';

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

  it('translates every error code the backend can return (read from the Python sources)', () => {
    const backend = path.resolve(import.meta.dirname, '../../../backend/app');
    const files: string[] = [];
    const walk = (dir: string) => {
      for (const name of readdirSync(dir)) {
        const full = path.join(dir, name);
        if (statSync(full).isDirectory()) walk(full);
        else if (name.endsWith('.py')) files.push(full);
      }
    };
    walk(backend);
    const codes = new Set<string>();
    const patterns = [/AppError\(\s*\d+,\s*"([a-z_.]+)"/g, /Issue\(\s*"([a-z_.]+)"/g, /ExcelFileError\(\s*"([a-z_.]+)"/g, /SettingViolation\(\s*"([a-z_.]+)"/g, /fail\("([a-z_.]+)"/g];
    for (const file of files) {
      const source = readFileSync(file, 'utf8');
      for (const pattern of patterns) for (const match of source.matchAll(pattern)) codes.add(match[1] ?? '');
    }
    expect(codes.size).toBeGreaterThan(80);
    for (const lang of ['en', 'es', 'fr'] as const) {
      expect([...codes].filter((c) => !locales[lang].has(`errors.${c}`))).toEqual([]);
    }
  });
});
