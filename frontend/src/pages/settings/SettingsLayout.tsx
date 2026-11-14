import { useTranslation } from 'react-i18next';
import { NavLink, Outlet } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';
import { SETTINGS_TAB_LABELS, settingsTabs } from '@/lib/navigation';
import type { Me, PublicConfig } from '@/types/api';

export function SettingsLayout({ me, config }: { me: Me; config: PublicConfig }): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-4">
      <PageHeader title={t('settings.title')} description={t('settings.description')} />
      <nav aria-label={t('settings.title')} className="flex flex-wrap gap-0.5 border-b border-line">
        {settingsTabs(me, config).map((tab) => (
          <NavLink
            key={tab}
            to={`/settings/${tab}`}
            className="-mb-px inline-flex min-h-10 items-center border-b-2 border-transparent px-3.5 py-2 font-medium aria-[current=page]:border-accent aria-[current=page]:text-accent"
          >
            {t(SETTINGS_TAB_LABELS[tab] ?? tab)}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
