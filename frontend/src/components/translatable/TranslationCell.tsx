import { useTranslation } from 'react-i18next';

import { Badge } from '@/components/ui/badge';
import type { Language } from '@/i18n';
import { translationOf, type TranslatableText } from '@/types/translatable';

/** One language of a TranslatableText in a table cell; a missing translation says so. */
export function TranslationCell({ text, language }: { text: TranslatableText; language: Language }): React.JSX.Element {
  const { t } = useTranslation();
  const value = translationOf(text, language);
  if (value === null) {
    return <Badge tone="warn">{t('translatable.missing', { lang: t(`languages.short.${language}`) })}</Badge>;
  }
  return <span lang={language}>{value}</span>;
}
