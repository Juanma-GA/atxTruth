import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PageHeader } from '@/components/layout/PageHeader';
import { Card } from '@/components/ui/card';
import { Field } from '@/components/ui/field';
import { Select } from '@/components/ui/input';
import { Pagination } from '@/components/ui/pagination';
import { Table, TableWrap, Td, Th } from '@/components/ui/table';
import { useAudit } from '@/hooks/useAudit';
import { useClientConfig } from '@/hooks/useConfig';
import { useSettings } from '@/hooks/useSettings';
import { TranslatedText } from '@/components/translatable/TranslatedText';
import { humanizeToken } from '@/lib/humanize';
import { errorMessage } from '@/services/apiErrors';
import type { AuditEvent } from '@/types/api';

const FILTERS = ['', 'auth.', 'user.', 'settings.', 'account.'] as const;
const FILTER_KEYS: Record<(typeof FILTERS)[number], string> = {
  '': 'all',
  'auth.': 'auth',
  'user.': 'user',
  'settings.': 'settings',
  'account.': 'account',
};

function useFormatValue() {
  const { t, i18n } = useTranslation();
  return (field: string, value: unknown): string => {
    if (value === null || value === undefined) return t('common.none');
    if (field === 'role' && typeof value === 'string') return t(`roles.${value}`);
    if (field === 'theme' && typeof value === 'string') return t(`theme.${value}`);
    if (field === 'preferred_language' && typeof value === 'string') return t(`languages.${value}`);
    if (field === 'deleted_at' && typeof value === 'string') return new Date(value).toLocaleString(i18n.language);
    if (typeof value === 'object') {
      return Object.entries(value as Record<string, unknown>)
        .map(([k, v]) => `${humanizeToken(k)}: ${String(v)}`)
        .join(', ');
    }
    return String(value);
  };
}

function Changes({ event }: { event: AuditEvent }): React.JSX.Element | null {
  const { t, i18n } = useTranslation();
  const format = useFormatValue();
  const before = event.before ?? {};
  const after = event.after ?? {};
  const fields = [...new Set([...Object.keys(before), ...Object.keys(after)])].filter(
    (f) => JSON.stringify(before[f]) !== JSON.stringify(after[f]) || !event.before,
  );
  if (fields.length === 0) return null;
  const label = (f: string) => (i18n.exists(`audit.fields.${f}`) ? t(`audit.fields.${f}`) : humanizeToken(f));
  return (
    <ul className="m-0 flex list-none flex-col gap-0.5 p-0 text-[12.5px]">
      {fields.map((f) => (
        <li key={f}>
          <span className="text-muted">{label(f)}:</span>{' '}
          {event.before ? (
            <>
              <span className="line-through decoration-muted">{format(f, before[f])}</span> →{' '}
            </>
          ) : null}
          <span>{format(f, after[f])}</span>
        </li>
      ))}
    </ul>
  );
}

export function AuditPage(): React.JSX.Element {
  const { t, i18n } = useTranslation();
  const config = useClientConfig();
  const pageSize = config.data?.table_page_size ?? 25;
  const [page, setPage] = useState(1);
  const [action, setAction] = useState<(typeof FILTERS)[number]>('');
  const audit = useAudit(page, pageSize, action);
  const settings = useSettings();
  const settingLabels = useMemo(
    () => new Map((settings.data ?? []).map((setting) => [setting.key, setting.label])),
    [settings.data],
  );
  const target = (event: AuditEvent) => {
    const label = event.target_type === 'app_setting' && event.target_id ? settingLabels.get(event.target_id) : undefined;
    if (label) return <TranslatedText text={label} />;
    return <span className="font-mono text-[12.5px]">{event.target_label ?? t('common.none')}</span>;
  };
  const dateFormat = useMemo(
    () => new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium', timeStyle: 'medium' }),
    [i18n.language],
  );
  const actionLabel = (code: string) => (i18n.exists(`audit.actions.${code}`) ? t(`audit.actions.${code}`) : humanizeToken(code));

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t('audit.title')} description={t('audit.description')} />
      <Field id="audit-filter" label={t('audit.filterLabel')} className="max-w-72">
        <Select
          value={action}
          onChange={(e) => {
            setAction(e.target.value as (typeof FILTERS)[number]);
            setPage(1);
          }}
        >
          {FILTERS.map((f) => (
            <option key={f} value={f}>
              {t(`audit.filter.${FILTER_KEYS[f]}`)}
            </option>
          ))}
        </Select>
      </Field>
      {audit.isError ? <p role="alert" className="text-bad">{errorMessage(t, audit.error)}</p> : null}
      <Card>
        <TableWrap>
          <Table>
            <thead>
              <tr>
                <Th scope="col">{t('audit.when')}</Th>
                <Th scope="col">{t('audit.who')}</Th>
                <Th scope="col">{t('audit.action')}</Th>
                <Th scope="col">{t('audit.target')}</Th>
                <Th scope="col">{t('audit.changes')}</Th>
              </tr>
            </thead>
            <tbody>
              {audit.isPending ? (
                <tr>
                  <Td colSpan={5} className="text-muted">
                    {t('common.loading')}
                  </Td>
                </tr>
              ) : (audit.data?.items.length ?? 0) === 0 ? (
                <tr>
                  <Td colSpan={5} className="text-muted">
                    {t('audit.empty')}
                  </Td>
                </tr>
              ) : (
                audit.data?.items.map((event) => (
                  <tr key={event.id} data-action={event.action}>
                    <Td className="whitespace-nowrap">{dateFormat.format(new Date(event.occurred_at))}</Td>
                    <Td className="font-mono text-[12.5px]">{event.actor_email ?? t('audit.system')}</Td>
                    <Td>{actionLabel(event.action)}</Td>
                    <Td>{target(event)}</Td>
                    <Td>
                      <Changes event={event} />
                    </Td>
                  </tr>
                ))
              )}
            </tbody>
          </Table>
        </TableWrap>
        <Pagination
          page={page}
          pages={Math.ceil((audit.data?.total ?? 0) / pageSize)}
          total={audit.data?.total ?? 0}
          onPage={setPage}
        />
      </Card>
    </div>
  );
}
