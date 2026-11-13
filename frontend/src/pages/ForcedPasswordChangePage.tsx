import { useTranslation } from 'react-i18next';

import { Brand } from '@/components/layout/Brand';
import { ChangePasswordForm } from '@/components/settings/ChangePasswordForm';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useSignOut } from '@/hooks/useSession';
import type { PublicConfig } from '@/types/api';

export function ForcedPasswordChangePage({ config }: { config: PublicConfig }): React.JSX.Element {
  const { t } = useTranslation();
  const signOut = useSignOut();
  return (
    <div className="flex min-h-full flex-col">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line bg-panel px-4 py-2">
        <Brand appName={config.app_name} />
        <Button variant="ghost" onClick={() => void signOut()}>
          {t('shell.signOut')}
        </Button>
      </header>
      <main id="main" className="grid flex-1 place-items-center p-4">
        <Card className="w-full max-w-[460px]">
          <CardContent className="flex flex-col gap-4 p-5">
            <div>
              <h1 className="text-[22px]">{t('changePassword.title')}</h1>
              <p className="m-0 text-muted">{t('changePassword.forcedIntro')}</p>
            </div>
            <ChangePasswordForm minLength={config.password_min_length} />
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
