import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/ui/button';
import { usePublicConfig } from '@/hooks/useConfig';
import { useMe } from '@/hooks/useMe';
import { applyLanguage, type Language } from '@/i18n';
import { settingsTabs } from '@/lib/navigation';
import { applyTheme } from '@/lib/theme';
import { ForcedPasswordChangePage } from '@/pages/ForcedPasswordChangePage';
import { HomePage } from '@/pages/HomePage';
import { LoginPage } from '@/pages/LoginPage';
import { AccountPage } from '@/pages/settings/AccountPage';
import { AuditPage } from '@/pages/settings/AuditPage';
import { ConfigurationPage } from '@/pages/settings/ConfigurationPage';
import { SettingsLayout } from '@/pages/settings/SettingsLayout';
import { UsersPage } from '@/pages/settings/UsersPage';
import { onSessionExpired, refreshSession } from '@/services/api';
import { errorMessage } from '@/services/apiErrors';
import { queryKeys } from '@/services/queryKeys';
import { useAuthStore } from '@/stores/auth';
import { useUiStore } from '@/stores/ui';
import type { Me, PublicConfig } from '@/types/api';

function FullPageMessage({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <div className="grid h-full place-items-center p-4 text-center text-muted">{children}</div>;
}

/** Restores the session from the HttpOnly refresh cookie on load. */
function useSessionRestore(): { error: unknown; retry: () => void } {
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false;
    refreshSession()
      .then((ok) => {
        if (!cancelled && !ok) useAuthStore.getState().clear();
      })
      .catch((err: unknown) => {
        // The server did not answer: the session is unknown, not gone. Say so and offer a retry.
        if (!cancelled) setError(err);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);
  return {
    error,
    retry: () => {
      setError(null);
      setAttempt((n) => n + 1);
    },
  };
}

function AuthenticatedApp({ me, config, language }: { me: Me; config: PublicConfig; language: Language }): React.JSX.Element {
  if (me.must_change_password) return <ForcedPasswordChangePage config={config} />;
  const isAdmin = me.role === 'admin';
  const tabs = settingsTabs(me, config);
  return (
    <Routes>
      <Route element={<AppShell me={me} config={config} language={language} />}>
        <Route index element={<HomePage me={me} />} />
        <Route path="settings" element={<SettingsLayout me={me} config={config} />}>
          <Route index element={<Navigate to="account" replace />} />
          <Route path="account" element={<AccountPage me={me} config={config} language={language} />} />
          {isAdmin ? <Route path="configuration" element={<ConfigurationPage />} /> : null}
          {tabs.includes('users') ? <Route path="users" element={<UsersPage me={me} />} /> : null}
          {isAdmin ? <Route path="audit" element={<AuditPage />} /> : null}
          <Route path="*" element={<Navigate to="/settings/account" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export function App(): React.JSX.Element {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const status = useAuthStore((s) => s.status);
  const anonymousLanguage = useUiStore((s) => s.anonymousLanguage);
  const config = usePublicConfig();
  const me = useMe();
  const restore = useSessionRestore();

  useEffect(() => {
    onSessionExpired(() => {
      queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== queryKeys.publicConfig[0] });
      toast.error(t('shell.sessionExpired'));
      navigate('/login');
    });
  }, [navigate, queryClient, t]);

  const language: Language =
    (status === 'authenticated' ? me.data?.preferred_language : anonymousLanguage) ??
    config.data?.default_language ??
    'en';
  useEffect(() => applyLanguage(language), [language]);
  useEffect(() => applyTheme(status === 'authenticated' && me.data ? me.data.theme : 'system'), [status, me.data]);
  useEffect(() => {
    if (config.data) document.title = config.data.app_name;
  }, [config.data]);

  if (restore.error || config.isError) {
    return (
      <FullPageMessage>
        <div className="flex flex-col items-center gap-3">
          <p role="alert" className="m-0">
            {errorMessage(t, restore.error ?? config.error)}
          </p>
          <Button
            onClick={() => {
              restore.retry();
              void config.refetch();
            }}
          >
            {t('common.retry')}
          </Button>
        </div>
      </FullPageMessage>
    );
  }
  if (!config.data || status === 'checking' || (status === 'authenticated' && !me.data)) {
    return <FullPageMessage>{t('common.loading')}</FullPageMessage>;
  }

  if (status === 'anonymous' || !me.data) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage config={config.data} language={language} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route path="/*" element={<AuthenticatedApp me={me.data} config={config.data} language={language} />} />
    </Routes>
  );
}
