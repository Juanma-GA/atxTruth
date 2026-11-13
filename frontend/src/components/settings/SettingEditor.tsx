import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { TranslatedText } from '@/components/translatable/TranslatedText';
import { Input, Select } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { humanizeToken } from '@/lib/humanize';
import { localViolation } from '@/lib/settingValidation';
import type { Setting, SettingProperty, SettingValue } from '@/types/api';

interface NumberFieldProps {
  id: string;
  labelledBy: string;
  value: number;
  type: 'integer' | 'number';
  rules: { min?: number; max?: number; unit?: string };
  describedBy?: string;
  onCommit: (value: number) => void;
}

function NumberField({ id, labelledBy, value, type, rules, describedBy, onCommit }: NumberFieldProps): React.JSX.Element {
  const { t } = useTranslation();
  const [draft, setDraft] = useState(String(value));
  const [error, setError] = useState<string | null>(null);
  useEffect(() => setDraft(String(value)), [value]);

  const commit = () => {
    const parsed = draft.trim() === '' ? Number.NaN : Number(draft);
    const violation = localViolation(type, rules, parsed);
    if (violation) {
      setError(t(violation.key, violation.params));
      return;
    }
    setError(null);
    if (parsed !== value) onCommit(parsed);
  };

  return (
    <div className="flex min-w-0 flex-col gap-1">
      <div className="flex items-center gap-2">
        <Input
          id={id}
          aria-labelledby={labelledBy}
          inputMode={type === 'integer' ? 'numeric' : 'decimal'}
          className="max-w-36"
          value={draft}
          aria-invalid={Boolean(error)}
          aria-describedby={[describedBy, error ? `${id}-error` : null].filter(Boolean).join(' ') || undefined}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit();
          }}
        />
        {rules.unit ? <span className="text-[13px] text-muted">{t(`config.units.${rules.unit}`)}</span> : null}
      </div>
      {error ? (
        <p id={`${id}-error`} role="alert" className="m-0 text-xs font-medium text-bad">
          {error}
        </p>
      ) : null}
    </div>
  );
}

interface Props {
  setting: Setting;
  labelId: string;
  describedBy: string;
  onCommit: (value: SettingValue) => void;
}

export function SettingEditor({ setting, labelId, describedBy, onCommit }: Props): React.JSX.Element {
  const { t } = useTranslation();
  const id = `setting-${setting.key.replace(/\W/g, '-')}`;
  const [text, setText] = useState(typeof setting.value === 'string' ? setting.value : '');
  const [textError, setTextError] = useState<string | null>(null);
  useEffect(() => {
    if (typeof setting.value === 'string') setText(setting.value);
  }, [setting.value]);

  switch (setting.value_type) {
    case 'integer':
    case 'number':
      return (
        <NumberField
          id={id}
          labelledBy={labelId}
          value={setting.value as number}
          type={setting.value_type}
          rules={setting.constraints}
          describedBy={describedBy}
          onCommit={onCommit}
        />
      );
    case 'boolean':
      return (
        <div className="flex items-center gap-2">
          <Switch
            id={id}
            aria-labelledby={labelId}
            aria-describedby={describedBy}
            checked={setting.value === true}
            onCheckedChange={(checked) => onCommit(checked)}
          />
          <span className="text-[13px]">{setting.value ? t('common.on') : t('common.off')}</span>
        </div>
      );
    case 'enum':
      return (
        <Select
          id={id}
          className="max-w-60"
          aria-labelledby={labelId}
          aria-describedby={describedBy}
          value={String(setting.value)}
          onChange={(e) => onCommit(e.target.value)}
        >
          {(setting.constraints.options ?? []).map((option) => (
            <option key={option} value={option}>
              {/* Option values are language codes today; translate known vocabularies. */}
              {t(`languages.${option}`)}
            </option>
          ))}
        </Select>
      );
    case 'object': {
      const value = setting.value as Record<string, unknown>;
      const properties: [string, SettingProperty][] = Object.entries(setting.constraints.properties ?? {});
      return (
        <div className="grid gap-3 sm:grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
          {properties.map(([name, prop]) => (
            <div key={name} className="flex flex-col gap-1">
              <span className="text-xs font-medium text-muted" id={`${id}-${name}-label`}>
                {prop.label ? <TranslatedText text={prop.label} /> : humanizeToken(name)}
              </span>
              <NumberField
                id={`${id}-${name}`}
                labelledBy={`${labelId} ${id}-${name}-label`}
                value={value[name] as number}
                type={prop.type === 'number' ? 'number' : 'integer'}
                rules={prop}
                describedBy={describedBy}
                onCommit={(v) => onCommit({ [name]: v })}
              />
            </div>
          ))}
        </div>
      );
    }
    case 'string':
    default:
      return (
        <div className="flex flex-col gap-1">
          <Input
            id={id}
            className="max-w-96"
            aria-labelledby={labelId}
            value={text}
            maxLength={setting.constraints.max_length}
            aria-invalid={Boolean(textError)}
            aria-describedby={[describedBy, textError ? `${id}-error` : null].filter(Boolean).join(' ')}
            onChange={(e) => setText(e.target.value)}
            onBlur={() => {
              const violation = localViolation('string', setting.constraints, text);
              if (violation) {
                setTextError(t(violation.key, violation.params));
                return;
              }
              setTextError(null);
              if (text !== setting.value) onCommit(text.trim());
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') e.currentTarget.blur();
            }}
          />
          {textError ? (
            <p id={`${id}-error`} role="alert" className="m-0 text-xs font-medium text-bad">
              {textError}
            </p>
          ) : null}
        </div>
      );
  }
}
