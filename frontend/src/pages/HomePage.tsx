import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Me } from '@/types/api';

export function HomePage({ me }: { me: Me }): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-5">
      <PageHeader title={t('home.welcome', { name: me.display_name })} description={t('home.description')} />
      <div className="grid gap-4 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>{t('home.statusTitle')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="m-0 max-w-[62ch] text-muted">{t('home.statusBody')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t('home.accountTitle')}</CardTitle>
            <Badge tone="info">{t(`roles.${me.role}`)}</Badge>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p className="m-0">{t('home.roleLine', { role: t(`roles.${me.role}`) })}</p>
            <p className="m-0 font-mono text-[12.5px] text-muted">{me.email}</p>
            <div>
              <Button asChild>
                <Link to="/settings">{t('home.openSettings')}</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
