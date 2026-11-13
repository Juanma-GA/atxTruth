import { RotateCcw } from 'lucide-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { SettingEditor } from '@/components/settings/SettingEditor';
import { TranslatedText } from '@/components/translatable/TranslatedText';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useInfrastructure, useSettings, useUpdateSetting } from '@/hooks/useSettings';
import { errorMessage } from '@/services/apiErrors';
import type { Setting, SettingValue } from '@/types/api';

const CATEGORY_ORDER = ['general', 'security', 'interface', 'content'];

function formatValue(setting: Setting, value: SettingValue, t: (k: string, o?: Record<string, unknown>) => string): string {
  if (setting.value_type === 'enum') return t(`languages.${String(value)}`);
  if (setting.value_type === 'boolean') return value ? t('common.on') : t('common.off');
  if (setting.value_type === 'object' && typeof value === 'object') {
    return Object.entries(setting.constraints.properties ?? {})
      .map(([name, prop]) => {
        const unit = prop.unit ? ` ${t(`config.units.${prop.unit}`)}` : '';
        return `${String((value as Record<string, unknown>)[name])}${unit}`;
      })
      .join(' · ');
  }
  const unit = setting.constraints.unit ? ` ${t(`config.units.${setting.constraints.unit}`)}` : '';
  return `${String(value)}${unit}`;
}

export function ConfigurationPage(): React.JSX.Element {
  const { t } = useTranslation();
  const settings = useSettings();
  const infrastructure = useInfrastructure();
  const update = useUpdateSetting();

  const groups = useMemo(() => {
    const map = new Map<string, Setting[]>();
    for (const setting of settings.data ?? []) {
      map.set(setting.category, [...(map.get(setting.category) ?? []), setting]);
    }
    const rank = (category: string) => {
      const index = CATEGORY_ORDER.indexOf(category);
      return index === -1 ? CATEGORY_ORDER.length : index;
    };
    return [...map.entries()].sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b));
  }, [settings.data]);

  if (settings.isPending) return <p className="text-muted">{t('common.loading')}</p>;
  if (settings.isError) return <p role="alert" className="text-bad">{errorMessage(t, settings.error)}</p>;

  return (
    <div className="flex flex-col gap-4">
      <p className="m-0 text-muted">{t('config.description')}</p>
      {groups.map(([category, items]) => (
        <Card key={category}>
          <CardHeader>
            <CardTitle>{t(`config.categories.${category}`)}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col divide-y divide-line2 p-0">
            {items.map((setting) => {
              const slug = setting.key.replace(/\W/g, '-');
              const descId = `setting-desc-${slug}`;
              const labelId = `setting-label-${slug}`;
              const isDefault = JSON.stringify(setting.value) === JSON.stringify(setting.default_value);
              return (
                <div
                  key={setting.key}
                  data-setting={setting.key}
                  className="grid gap-3 px-3.5 py-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_auto] md:items-start"
                >
                  <div className="min-w-0">
                    <h4 id={labelId} className="m-0 font-ui text-[13.5px] font-semibold">
                      <TranslatedText text={setting.label} />
                    </h4>
                    <p id={descId} className="m-0 text-[12.5px] text-muted">
                      <TranslatedText text={setting.description} />
                    </p>
                  </div>
                  <SettingEditor
                    setting={setting}
                    labelId={labelId}
                    describedBy={descId}
                    onCommit={(value) => update.mutate({ key: setting.key, value })}
                  />
                  <div className="flex flex-col items-start gap-1 md:items-end">
                    <span className="text-xs text-muted">
                      {t('config.defaultValue', { value: formatValue(setting, setting.default_value, t) })}
                    </span>
                    {!isDefault ? (
                      <Button size="sm" variant="ghost" onClick={() => update.mutate({ key: setting.key, reset: true })}>
                        <RotateCcw aria-hidden="true" />
                        {t('config.restoreDefault')}
                      </Button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      ))}
      <Card>
        <CardHeader>
          <CardTitle>{t('config.infraTitle')}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="m-0 text-[13px] text-muted">{t('config.infraDescription')}</p>
          {infrastructure.isError ? <p role="alert" className="text-bad">{errorMessage(t, infrastructure.error)}</p> : null}
          <dl className="m-0 grid gap-x-4 gap-y-2 sm:grid-cols-[max-content_minmax(0,1fr)]">
            {(infrastructure.data ?? []).map((item) => (
              <div key={item.key} className="contents">
                <dt className="font-mono text-[12.5px] text-muted">{item.key}</dt>
                <dd className="m-0 flex min-w-0 items-center gap-2 font-mono text-[12.5px] break-all">
                  {item.value}
                  {item.secret ? <Badge tone="warn">{t('config.secret')}</Badge> : null}
                </dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
