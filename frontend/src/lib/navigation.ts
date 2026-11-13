import type { Me, PublicConfig } from '@/types/api';

/** Settings sections the user may open (the server enforces the same rules). */
export function settingsTabs(me: Me, config: PublicConfig): string[] {
  const tabs = ['account'];
  if (me.role === 'admin') {
    tabs.push('configuration');
    if (config.auth_mode === 'local') tabs.push('users');
    tabs.push('audit');
  }
  return tabs;
}
