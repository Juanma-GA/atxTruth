import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Badge, type BadgeProps } from '@/components/ui/badge';
import { Field } from '@/components/ui/field';
import { Select } from '@/components/ui/input';
import { Table, TableWrap, Td, Th } from '@/components/ui/table';
import { codeMessage } from '@/services/apiErrors';
import type { ImportReport, Issue, ReportRow, RowAction } from '@/types/excel';

const FILTERS = ['all', 'errors', 'create', 'update', 'delete', 'warnings', 'unchanged'] as const;
type Filter = (typeof FILTERS)[number];

const TONE: Record<RowAction, BadgeProps['tone']> = {
  create: 'ok',
  update: 'info',
  delete: 'warn',
  unchanged: 'plain',
  error: 'bad',
};
const SUMMARY_KEYS = ['create', 'update', 'delete', 'unchanged', 'errors', 'warnings', 'not_in_file', 'special_values'] as const;

function useValue() {
  const { t } = useTranslation();
  return (value: unknown): string => {
    if (value === null || value === undefined || value === '' || (Array.isArray(value) && value.length === 0)) {
      return t('excel.emptyValue');
    }
    if (typeof value === 'boolean') return value ? t('common.yes') : t('common.no');
    if (Array.isArray(value)) return value.join('/');
    return String(value);
  };
}

function IssueLine({ issue, tone }: { issue: Issue; tone: 'bad' | 'warn' }): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <li className={tone === 'bad' ? 'text-bad' : 'text-warn'}>
      {issue.column ? <span className="font-mono text-[12px]">{issue.column}: </span> : null}
      {codeMessage(t, issue.code, issue.params)}
    </li>
  );
}

function matches(row: ReportRow, filter: Filter): boolean {
  switch (filter) {
    case 'all':
      return row.action !== 'unchanged' || row.errors.length > 0 || row.warnings.length > 0;
    case 'errors':
      return row.errors.length > 0;
    case 'warnings':
      return row.warnings.length > 0;
    default:
      return row.action === filter && row.errors.length === 0;
  }
}

/** The Analyze / Apply report: summary on top, then rows filterable by kind of change, errors first. */
export function ImportReportView({ report }: { report: ImportReport }): React.JSX.Element {
  const { t } = useTranslation();
  const format = useValue();
  const [filter, setFilter] = useState<Filter>(report.ok ? 'all' : 'errors');

  const rows = useMemo(() => {
    const all = report.sheets.flatMap((sheet) => sheet.rows.map((row) => ({ sheet: sheet.sheet, row })));
    return all
      .filter(({ row }) => matches(row, filter))
      .sort((a, b) => Number(b.row.errors.length > 0) - Number(a.row.errors.length > 0));
  }, [report, filter]);
  const notInFile = report.sheets.reduce((n, s) => n + s.not_in_file.length, 0);
  const specials = Object.entries(report.special_values).flatMap(([state, columns]) =>
    Object.entries(columns).map(([column, count]) => ({ state, column, count })),
  );

  return (
    <div className="flex flex-col gap-3" data-testid="import-report">
      <dl className="m-0 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {SUMMARY_KEYS.map((key) => (
          <div key={key} className="rounded-small border border-line2 bg-sunk px-2.5 py-1.5" data-summary={key}>
            <dt className="text-xs text-muted">{t(`excel.summary.${key}`)}</dt>
            <dd className={`m-0 text-lg font-semibold ${key === 'errors' && report.summary.errors > 0 ? 'text-bad' : ''}`}>
              {report.summary[key]}
            </dd>
          </div>
        ))}
      </dl>

      {report.errors.length > 0 ? (
        <div role="alert" className="rounded-base bg-bad-soft px-3 py-2">
          <p className="m-0 font-semibold text-bad">{t('excel.fileErrors')}</p>
          <ul className="m-0 pl-5 text-[13px]">
            {report.errors.map((issue, index) => (
              <IssueLine key={`${issue.code}-${index}`} issue={issue} tone="bad" />
            ))}
          </ul>
        </div>
      ) : null}
      {report.warnings.length > 0 ? (
        <ul className="m-0 rounded-base bg-warn-soft py-2 pr-3 pl-7 text-[13px]">
          {report.warnings.map((issue, index) => (
            <IssueLine key={`${issue.code}-${index}`} issue={issue} tone="warn" />
          ))}
        </ul>
      ) : null}
      {notInFile > 0 ? <p className="m-0 text-[13px] text-muted">{t('excel.notInFile', { count: notInFile })}</p> : null}
      {specials.length > 0 ? (
        <div className="text-[13px]">
          <p className="m-0 font-semibold">{t('excel.specialTitle')}</p>
          <ul className="m-0 pl-5 text-muted">
            {specials.map(({ state, column, count }) => (
              <li key={`${state}-${column}`}>
                {t('excel.specialCount', { state: t(`fieldState.${state}`), column, count })}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <Field id="report-filter" label={t('excel.filter.label')} className="max-w-72">
        <Select value={filter} onChange={(e) => setFilter(e.target.value as Filter)}>
          {FILTERS.map((f) => (
            <option key={f} value={f}>
              {t(`excel.filter.${f}`)}
            </option>
          ))}
        </Select>
      </Field>
      <TableWrap className="max-h-[50vh] overflow-y-auto rounded-base border border-line">
        <Table>
          <thead className="sticky top-0">
            <tr>
              <Th scope="col">{t('excel.columns.sheet')}</Th>
              <Th scope="col">{t('excel.columns.row')}</Th>
              <Th scope="col">{t('excel.columns.key')}</Th>
              <Th scope="col">{t('excel.columns.action')}</Th>
              <Th scope="col">{t('excel.columns.details')}</Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <Td colSpan={5} className="text-muted">
                  {t('excel.noRows')}
                </Td>
              </tr>
            ) : (
              rows.map(({ sheet, row }) => {
                const action: RowAction = row.errors.length > 0 ? 'error' : row.action;
                return (
                  <tr key={`${sheet}-${row.row ?? ''}-${row.key}`} data-report-row={`${sheet}:${row.key}`} data-action={action}>
                    <Td>{sheet}</Td>
                    <Td className="tabular-nums">{row.row ?? t('common.none')}</Td>
                    <Td className="font-mono text-[12.5px]">{row.key}</Td>
                    <Td>
                      <Badge tone={TONE[action]}>{t(`excel.actions.${action}`)}</Badge>
                    </Td>
                    <Td>
                      <ul className="m-0 flex list-none flex-col gap-0.5 p-0 text-[12.5px]">
                        {row.changes.map((change) => (
                          <li key={change.field}>
                            <span className="text-muted">{change.column}: </span>
                            {t('excel.change', { before: format(change.before), after: format(change.after) })}
                          </li>
                        ))}
                        {row.errors.map((issue, index) => (
                          <IssueLine key={`e-${index}`} issue={issue} tone="bad" />
                        ))}
                        {row.warnings.map((issue, index) => (
                          <IssueLine key={`w-${index}`} issue={issue} tone="warn" />
                        ))}
                      </ul>
                    </Td>
                  </tr>
                );
              })
            )}
          </tbody>
        </Table>
      </TableWrap>
    </div>
  );
}
