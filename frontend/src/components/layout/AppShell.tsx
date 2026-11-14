import { Home, ListChecks, Settings } from 'lucide-react';
import { Fragment } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';

import { useUpdateMe } from '@/hooks/useMe';
import type { Language } from '@/i18n';
import { SETTINGS_TAB_LABELS } from '@/lib/navigation';
import type { ThemePreference } from '@/lib/theme';
import type { Me, PublicConfig } from '@/types/api';

import { Brand } from './Brand';
import { LanguageSwitch } from './LanguageSwitch';
import { ThemeSwitch } from './ThemeSwitch';
import { UserMenu } from './UserMenu';

interface Crumb {
  label: string;
  to?: string;
}

function useCrumbs(): Crumb[] {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  if (pathname.startsWith('/settings')) {
    const section = pathname.split('/')[2];
    const crumbs: Crumb[] = [{ label: t('nav.settings'), to: '/settings' }];
    const labelKey = section ? SETTINGS_TAB_LABELS[section] : undefined;
    if (labelKey) crumbs.push({ label: t(labelKey) });
    return crumbs;
  }
  if (pathname.startsWith('/lists')) return [{ label: t('nav.lists'), to: pathname === '/lists' ? undefined : '/lists' }];
  return [{ label: t('nav.home') }];
}

const navItems = [
  { to: '/', key: 'nav.home', icon: Home, end: true },
  { to: '/lists', key: 'nav.lists', icon: ListChecks, end: false },
  { to: '/settings', key: 'nav.settings', icon: Settings, end: false },
] as const;

export function AppShell({ me, config, language }: { me: Me; config: PublicConfig; language: Language }): React.JSX.Element {
  const { t } = useTranslation();
  const updateMe = useUpdateMe();
  const crumbs = useCrumbs();

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_1fr] max-[860px]:h-auto max-[860px]:min-h-full">
      <a
        href="#main"
        className="sr-only z-50 rounded-base bg-accent px-3 py-2 text-accent-ink focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        {t('shell.skipToContent')}
      </a>
      <header className="flex flex-wrap items-center gap-4 border-b border-line bg-panel px-4 py-2">
        <Brand appName={config.app_name} />
        <nav aria-label={t('shell.breadcrumb')} className="min-w-0 flex-[1_1_160px] truncate text-[13px] text-muted">
          <ol className="m-0 flex list-none items-center gap-1.5 p-0">
            {crumbs.map((crumb, index) => {
              const last = index === crumbs.length - 1;
              return (
                <Fragment key={crumb.label}>
                  {index > 0 ? <li aria-hidden="true">›</li> : null}
                  <li className="truncate">
                    {last || !crumb.to ? (
                      <strong className="font-semibold text-ink" aria-current={last ? 'page' : undefined}>
                        {crumb.label}
                      </strong>
                    ) : (
                      <Link to={crumb.to} className="text-muted hover:text-ink">
                        {crumb.label}
                      </Link>
                    )}
                  </li>
                </Fragment>
              );
            })}
          </ol>
        </nav>
        <div className="flex flex-wrap items-center gap-2">
          <LanguageSwitch value={language} onChange={(lang) => updateMe.mutate({ preferred_language: lang })} />
          <ThemeSwitch value={me.theme} onChange={(theme: ThemePreference) => updateMe.mutate({ theme })} />
          <UserMenu me={me} canChangePassword={config.auth_mode === 'local'} />
        </div>
      </header>
      <div className="grid min-h-0 grid-cols-[var(--spacing-rail)_minmax(0,1fr)] max-[860px]:grid-cols-[minmax(0,1fr)]">
        <nav
          aria-label={t('shell.mainNav')}
          className="flex flex-col gap-0.5 overflow-auto border-r border-line bg-panel px-2.5 py-3.5 max-[860px]:flex-row max-[860px]:border-r-0 max-[860px]:border-b max-[860px]:p-2"
        >
          {navItems.map(({ to, key, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className="flex min-h-10 w-full items-center gap-2.5 rounded-base px-2.5 py-2 text-[13.5px] aria-[current=page]:bg-accent-soft aria-[current=page]:font-semibold aria-[current=page]:text-accent max-[860px]:w-auto [&_svg]:size-4 [&_svg]:text-muted"
            >
              <Icon aria-hidden="true" />
              {t(key)}
            </NavLink>
          ))}
        </nav>
        <main id="main" tabIndex={-1} className="flex min-h-0 min-w-0 flex-col overflow-auto max-[860px]:overflow-visible">
          <div className="flex flex-1 flex-col gap-4 px-4 pt-5 pb-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
