import type { Language } from '@/i18n';

/** Business text published in EN (master, required), ES and FR (optional). Mirrors the backend. */
export interface TranslatableText {
  en: string;
  es?: string | null;
  fr?: string | null;
}

export const MASTER_LANGUAGE: Language = 'en';

export function translationOf(text: TranslatableText, language: Language): string | null {
  const value = text[language];
  return typeof value === 'string' && value.trim() !== '' ? value : null;
}

export function missingLanguages(text: TranslatableText): Language[] {
  return (['es', 'fr'] as const).filter((lang) => translationOf(text, lang) === null);
}

/** Normalise for saving: trims, drops blank optional languages. */
export function normalizeTranslatable(text: TranslatableText): TranslatableText {
  const result: TranslatableText = { en: text.en.trim() };
  for (const lang of ['es', 'fr'] as const) {
    const value = translationOf(text, lang);
    if (value !== null) result[lang] = value.trim();
  }
  return result;
}
