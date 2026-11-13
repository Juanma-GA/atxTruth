import { useTranslation } from 'react-i18next';

import logo from '@/assets/alten_logo.png';

export function Brand({ appName }: { appName: string }): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <img src={logo} alt={t('shell.logoAlt')} className="h-[30px] w-auto" />
      <div className="min-w-0">
        <b className="block font-head text-lg font-semibold whitespace-nowrap">{appName}</b>
        <small className="block text-[11.5px] tracking-[.06em] text-muted uppercase">{t('app.tagline')}</small>
      </div>
    </div>
  );
}
