import { useId, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Badge } from '@/components/ui/badge';
import { Input, Textarea } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LANGUAGES, type Language } from '@/i18n';
import { MASTER_LANGUAGE, missingLanguages, translationOf, type TranslatableText } from '@/types/translatable';

interface Props {
  label: string;
  value: TranslatableText;
  onChange: (value: TranslatableText) => void;
  multiline?: boolean;
  maxLength?: number;
  /** Shown under the EN field, e.g. when the form was submitted without the master text. */
  error?: string;
}

/**
 * Edits a TranslatableText: one tab per language, EN required, a visible marker on every language
 * that still has no translation.
 */
export function TranslatableTextEditor({ label, value, onChange, multiline = false, maxLength, error }: Props): React.JSX.Element {
  const { t } = useTranslation();
  const baseId = useId();
  const [active, setActive] = useState<Language>(MASTER_LANGUAGE);
  const missing = new Set(missingLanguages(value));
  const masterMissing = translationOf(value, MASTER_LANGUAGE) === null;
  const Control = multiline ? Textarea : Input;

  return (
    <div className="flex min-w-0 flex-col gap-1.5" role="group" aria-label={label}>
      <span className="text-xs font-medium text-muted">{label}</span>
      <Tabs value={active} onValueChange={(v) => setActive(v as Language)}>
        <TabsList aria-label={t('translatable.tabsLabel')}>
          {LANGUAGES.map((lang) => {
            const isMissing = lang === MASTER_LANGUAGE ? masterMissing : missing.has(lang);
            return (
              <TabsTrigger key={lang} value={lang}>
                <span lang={lang}>{t(`languages.short.${lang}`)}</span>
                {isMissing ? (
                  <span
                    className={`size-2 rounded-full ${lang === MASTER_LANGUAGE ? 'bg-bad' : 'bg-warn'}`}
                    aria-label={t('translatable.missing', { lang: t(`languages.short.${lang}`) })}
                    role="img"
                  />
                ) : null}
              </TabsTrigger>
            );
          })}
        </TabsList>
        {LANGUAGES.map((lang) => {
          const id = `${baseId}-${lang}`;
          const isMaster = lang === MASTER_LANGUAGE;
          const fieldError = isMaster && error ? error : undefined;
          return (
            <TabsContent key={lang} value={lang} className="flex flex-col gap-1 pt-2">
              <div className="flex items-center justify-between gap-2">
                <Label htmlFor={id}>{t('translatable.fieldInLanguage', { field: label, lang: t(`languages.${lang}`) })}</Label>
                {isMaster ? (
                  <Badge tone="info">{t('translatable.master')}</Badge>
                ) : missing.has(lang) ? (
                  <Badge tone="warn">{t('translatable.missing', { lang: t(`languages.short.${lang}`) })}</Badge>
                ) : (
                  <Badge>{t('translatable.optional')}</Badge>
                )}
              </div>
              <Control
                id={id}
                lang={lang}
                value={value[lang] ?? ''}
                maxLength={maxLength}
                required={isMaster}
                aria-invalid={Boolean(fieldError)}
                aria-describedby={fieldError ? `${id}-error` : undefined}
                onChange={(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
                  onChange({ ...value, [lang]: e.target.value })
                }
              />
              {fieldError ? (
                <p id={`${id}-error`} role="alert" className="m-0 text-xs font-medium text-bad">
                  {fieldError}
                </p>
              ) : null}
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}
