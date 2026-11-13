import { useTranslation } from 'react-i18next';

import { Segmented } from '@/components/ui/segmented';
import { LANGUAGES, type Language } from '@/i18n';

interface Props {
  value: Language;
  onChange: (language: Language) => void;
}

export function LanguageSwitch({ value, onChange }: Props): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <Segmented
      label={t('shell.language')}
      value={value}
      onChange={onChange}
      options={LANGUAGES.map((lang) => ({
        value: lang,
        label: <span lang={lang}>{t(`languages.short.${lang}`)}</span>,
        ariaLabel: t(`languages.${lang}`),
      }))}
    />
  );
}
