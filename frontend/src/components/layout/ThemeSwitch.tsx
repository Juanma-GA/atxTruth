import { Monitor, Moon, Sun } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Segmented } from '@/components/ui/segmented';
import type { ThemePreference } from '@/lib/theme';

interface Props {
  value: ThemePreference;
  onChange: (theme: ThemePreference) => void;
}

export function ThemeSwitch({ value, onChange }: Props): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <Segmented
      label={t('theme.label')}
      value={value}
      onChange={onChange}
      options={[
        { value: 'system', label: <Monitor aria-hidden="true" />, ariaLabel: t('theme.system') },
        { value: 'light', label: <Sun aria-hidden="true" />, ariaLabel: t('theme.light') },
        { value: 'dark', label: <Moon aria-hidden="true" />, ariaLabel: t('theme.dark') },
      ]}
    />
  );
}
