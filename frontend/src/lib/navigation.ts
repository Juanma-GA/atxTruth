import type { Me, PublicConfig } from '@/types/api';

/** Path segment under /settings → i18n key of its tab label. */
export const SETTINGS_TAB_LABELS: Record<string, string> = {
  account: 'settings.tabs.account',
  configuration: 'settings.tabs.configuration',
  users: 'settings.tabs.users',
  audit: 'settings.tabs.audit',
  'initial-data': 'settings.tabs.initialData',
};

/** Settings sections the user may open (the server enforces the same rules). */
export function settingsTabs(me: Me, config: PublicConfig): string[] {
  const tabs = ['account'];
  if (me.role === 'admin') {
    tabs.push('configuration');
    if (config.auth_mode === 'local') tabs.push('users');
    tabs.push('audit', 'initial-data');
  }
  return tabs;
}
