import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'react-router-dom';

import { ChangePasswordForm } from '@/components/settings/ChangePasswordForm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Field } from '@/components/ui/field';
import { Input, Select } from '@/components/ui/input';
import { useUpdateMe } from '@/hooks/useMe';
import { LANGUAGES, isLanguage, type Language } from '@/i18n';
import type { ThemePreference } from '@/lib/theme';
import type { Me, PublicConfig } from '@/types/api';

const THEMES: ThemePreference[] = ['system', 'light', 'dark'];

export function AccountPage({ me, config, language }: { me: Me; config: PublicConfig; language: Language }): React.JSX.Element {
  const { t } = useTranslation();
  const updateMe = useUpdateMe();
  const [name, setName] = useState(me.display_name);
  const passwordRef = useRef<HTMLDivElement>(null);
  const { hash } = useLocation();

  useEffect(() => setName(me.display_name), [me.display_name]);
  useEffect(() => {
    if (hash === '#password') passwordRef.current?.scrollIntoView({ block: 'start' });
  }, [hash]);

  const saveName = () => {
    const trimmed = name.trim();
    if (trimmed === '' || trimmed === me.display_name) {
      setName(me.display_name);
      return;
    }
    updateMe.mutate({ display_name: trimmed });
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="m-0 text-muted">{t('account.description')}</p>
      <Card>
        <CardHeader>
          <CardTitle>{t('account.profile')}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
          <Field id="acc-name" label={t('account.displayName')}>
            <Input
              value={name}
              maxLength={200}
              onChange={(e) => setName(e.target.value)}
              onBlur={saveName}
              onKeyDown={(e) => {
                if (e.key === 'Enter') e.currentTarget.blur();
              }}
            />
          </Field>
          <Field id="acc-email" label={t('account.email')}>
            <Input value={me.email} readOnly className="font-mono text-[12.5px]" />
          </Field>
          <Field id="acc-role" label={t('account.role')}>
            <Input value={t(`roles.${me.role}`)} readOnly />
          </Field>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{t('account.preferences')}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
          <Field id="acc-language" label={t('account.language')}>
            <Select
              value={language}
              onChange={(e) => {
                if (isLanguage(e.target.value)) updateMe.mutate({ preferred_language: e.target.value });
              }}
            >
              {LANGUAGES.map((lang) => (
                <option key={lang} value={lang}>
                  {t(`languages.${lang}`)}
                </option>
              ))}
            </Select>
          </Field>
          <Field id="acc-theme" label={t('account.theme')}>
            <Select value={me.theme} onChange={(e) => updateMe.mutate({ theme: e.target.value as ThemePreference })}>
              {THEMES.map((theme) => (
                <option key={theme} value={theme}>
                  {t(`theme.${theme}`)}
                </option>
              ))}
            </Select>
          </Field>
        </CardContent>
      </Card>
      {config.auth_mode === 'local' ? (
        <Card ref={passwordRef} id="password">
          <CardHeader>
            <CardTitle>{t('changePassword.title')}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p className="m-0 text-muted">{t('changePassword.intro')}</p>
            <ChangePasswordForm minLength={config.password_min_length} />
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
