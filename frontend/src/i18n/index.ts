import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import { humanizeToken } from '@/lib/humanize';

import en from './locales/en.json';
import es from './locales/es.json';
import fr from './locales/fr.json';

export const LANGUAGES = ['en', 'es', 'fr'] as const;
export type Language = (typeof LANGUAGES)[number];

export function isLanguage(value: unknown): value is Language {
  return typeof value === 'string' && (LANGUAGES as readonly string[]).includes(value);
}

export const resources = { en: { translation: en }, es: { translation: es }, fr: { translation: fr } };

void i18n.use(initReactI18next).init({
  resources,
  lng: 'en',
  // HR7: no silent fallback to another language. The key-parity test guarantees every key exists
  // in the three languages; if one ever slips through, it is shown humanized and reported.
  fallbackLng: false,
  interpolation: { escapeValue: false },
  returnNull: false,
  parseMissingKeyHandler: (key: string) => {
    console.error(`i18n: missing key "${key}"`);
    return humanizeToken(key.split('.').pop() ?? key);
  },
});

export function applyLanguage(language: Language): void {
  if (i18n.language !== language) void i18n.changeLanguage(language);
  document.documentElement.lang = language;
}

export default i18n;
