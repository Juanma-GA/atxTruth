import { useTranslation } from 'react-i18next';

import { Badge } from '@/components/ui/badge';
import { isLanguage, type Language } from '@/i18n';
import { MASTER_LANGUAGE, translationOf, type TranslatableText } from '@/types/translatable';

/**
 * Shows a TranslatableText in the interface language. When that translation is missing it says
 * so ("No FR translation") next to the English master text — never English without warning (HR7).
 */
export function TranslatedText({ text, className }: { text: TranslatableText; className?: string }): React.JSX.Element {
  const { t, i18n } = useTranslation();
  const language: Language = isLanguage(i18n.language) ? i18n.language : MASTER_LANGUAGE;
  const value = translationOf(text, language);
  if (value !== null) return <span className={className}>{value}</span>;
  return (
    <span className={className}>
      <span lang={MASTER_LANGUAGE}>{text.en}</span>{' '}
      <Badge tone="warn">{t('translatable.missing', { lang: t(`languages.short.${language}`) })}</Badge>
    </span>
  );
}
