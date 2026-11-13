import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';

import { Brand } from '@/components/layout/Brand';
import { LanguageSwitch } from '@/components/layout/LanguageSwitch';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Field } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { useSignIn } from '@/hooks/useSession';
import type { Language } from '@/i18n';
import { errorMessage } from '@/services/apiErrors';
import { useUiStore } from '@/stores/ui';
import type { PublicConfig } from '@/types/api';

const schema = z.object({
  email: z.string().trim().min(1, 'common.required'),
  password: z.string().min(1, 'common.required'),
});
type FormValues = z.infer<typeof schema>;

export function LoginPage({ config, language }: { config: PublicConfig; language: Language }): React.JSX.Element {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const signIn = useSignIn();
  const setLanguage = useUiStore((s) => s.setAnonymousLanguage);
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, handleSubmit, formState } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      await signIn(values.email, values.password);
      navigate('/', { replace: true });
    } catch (error) {
      setServerError(errorMessage(t, error));
    }
  });

  return (
    <div className="flex min-h-full flex-col">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line bg-panel px-4 py-2">
        <Brand appName={config.app_name} />
        <LanguageSwitch value={language} onChange={setLanguage} />
      </header>
      <main id="main" className="grid flex-1 place-items-center p-4">
        <Card className="w-full max-w-[400px]">
          <CardContent className="flex flex-col gap-4 p-5">
            <div>
              <h1 className="text-[22px]">{t('login.title')}</h1>
              <p className="m-0 text-muted">{config.auth_mode === 'local' ? t('login.subtitle') : t('login.ssoNotice')}</p>
            </div>
            {config.auth_mode === 'local' ? (
              <form className="flex flex-col gap-3" onSubmit={onSubmit} noValidate>
                <Field id="login-email" label={t('login.email')} error={formState.errors.email && t(formState.errors.email.message ?? '')}>
                  <Input type="email" autoComplete="username" autoFocus {...register('email')} />
                </Field>
                <Field
                  id="login-password"
                  label={t('login.password')}
                  error={formState.errors.password && t(formState.errors.password.message ?? '')}
                >
                  <Input type="password" autoComplete="current-password" {...register('password')} />
                </Field>
                {serverError ? (
                  <p role="alert" className="m-0 rounded-base bg-bad-soft px-3 py-2 text-[13px] font-medium text-bad">
                    {serverError}
                  </p>
                ) : null}
                <Button type="submit" variant="primary" disabled={formState.isSubmitting}>
                  {formState.isSubmitting ? t('login.submitting') : t('login.submit')}
                </Button>
              </form>
            ) : null}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
