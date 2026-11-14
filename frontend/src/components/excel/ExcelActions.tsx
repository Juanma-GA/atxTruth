import { useQueryClient } from '@tanstack/react-query';
import { Download, Upload } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Field } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { api } from '@/services/api';
import { ApiError, errorMessage } from '@/services/apiErrors';
import type { ImportReport } from '@/types/excel';

import { ImportReportView } from './ImportReportView';

interface ImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Base path: `${base}/analyze` and `${base}/apply` receive the file. */
  base: string;
  what: string;
  query?: string;
  /** Query keys to refresh after applying. */
  invalidate: readonly (readonly unknown[])[];
}

function isReport(value: unknown): value is ImportReport {
  return typeof value === 'object' && value !== null && 'sheets' in value && 'summary' in value;
}

/**
 * Upload → Analyze (dry run, writes nothing) → report → Apply (one transaction). Not optimistic
 * (HR20 exception): the result is computed by the server from the file.
 */
export function ImportDialog({ open, onOpenChange, base, what, query = '', invalidate }: ImportDialogProps): React.JSX.Element {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [busy, setBusy] = useState<'analyze' | 'apply' | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setFile(null);
    setReport(null);
    setError(null);
  };

  const run = async (step: 'analyze' | 'apply') => {
    if (!file) return;
    setBusy(step);
    setError(null);
    try {
      const result = await api.upload<ImportReport>(`${base}/${step}${query}`, file);
      setReport(result);
      if (step === 'apply') {
        invalidate.forEach((key) => void queryClient.invalidateQueries({ queryKey: key }));
        toast.success(t('excel.applied', result.summary));
        onOpenChange(false);
        reset();
      }
    } catch (err) {
      // A 409 on Apply carries the report of why nothing was written.
      const params = err instanceof ApiError ? err.params : {};
      if (isReport(params.report)) setReport(params.report);
      setError(errorMessage(t, err));
    } finally {
      setBusy(null);
    }
  };

  const changes = report ? report.summary.create + report.summary.update + report.summary.delete : 0;
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent
        title={t('excel.importTitle', { what })}
        className="max-w-[1100px]"
        footer={
          <>
            <Button onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
            {report ? (
              <Button onClick={reset} disabled={busy !== null}>
                {t('excel.anotherFile')}
              </Button>
            ) : null}
            {report ? (
              <Button variant="primary" disabled={!report.ok || changes === 0 || busy !== null} onClick={() => void run('apply')}>
                {busy === 'apply' ? t('excel.applying') : t('excel.apply')}
              </Button>
            ) : (
              <Button variant="primary" disabled={!file || busy !== null} onClick={() => void run('analyze')}>
                {busy === 'analyze' ? t('excel.analyzing') : t('excel.analyze')}
              </Button>
            )}
          </>
        }
      >
        {!report ? (
          <Field id="import-file" label={t('excel.chooseFile')} hint={t('excel.chooseHint')}>
            <Input
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </Field>
        ) : (
          <>
            <h3 className="m-0 text-[15px]">{t('excel.reportTitle', { file: report.file_name ?? file?.name ?? '' })}</h3>
            {!report.ok ? (
              <p role="alert" className="m-0 rounded-base bg-bad-soft px-3 py-2 text-[13px] font-medium text-bad">
                {t('excel.notApplied')}
              </p>
            ) : changes === 0 ? (
              <p className="m-0 text-[13px] text-muted">{t('excel.nothingToApply')}</p>
            ) : null}
            <ImportReportView report={report} />
          </>
        )}
        {error && !report ? (
          <p role="alert" className="m-0 text-[13px] font-medium text-bad">
            {error}
          </p>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

interface ExcelActionsProps {
  domain: 'lists' | 'taxonomy';
  canImport: boolean;
  edition?: string;
  invalidate: readonly (readonly unknown[])[];
}

/** "Export to Excel" (everyone) and "Import from Excel" (admins) for one domain. */
export function ExcelActions({ domain, canImport, edition, invalidate }: ExcelActionsProps): React.JSX.Element {
  const { t } = useTranslation();
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const query = edition ? `?edition=${encodeURIComponent(edition)}` : '';
  return (
    <>
      <Button
        disabled={exporting}
        onClick={() => {
          setExporting(true);
          api
            .download(`/api/excel/${domain}/export${query}`, `atxtruth-${domain}.xlsx`)
            .then(() => toast.success(t('excel.exported')))
            .catch((err: unknown) => toast.error(errorMessage(t, err)))
            .finally(() => setExporting(false));
        }}
      >
        <Download aria-hidden="true" />
        {t('excel.export')}
      </Button>
      {canImport ? (
        <>
          <Button onClick={() => setImporting(true)}>
            <Upload aria-hidden="true" />
            {t('excel.import')}
          </Button>
          <ImportDialog
            open={importing}
            onOpenChange={setImporting}
            base={`/api/excel/${domain}`}
            query={query}
            what={t(`excel.domains.${domain}`)}
            invalidate={invalidate}
          />
        </>
      ) : null}
    </>
  );
}
