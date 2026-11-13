import { useTranslation } from 'react-i18next';

import { Button } from './button';

interface Props {
  page: number;
  pages: number;
  total: number;
  onPage: (page: number) => void;
}

export function Pagination({ page, pages, total, onPage }: Props): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-3.5 py-2 text-[13px] text-muted">
      <span>{t('common.totalRows', { count: total })}</span>
      <div className="flex items-center gap-2">
        <Button size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          {t('common.previous')}
        </Button>
        <span aria-live="polite">{t('common.pageOf', { page, pages: Math.max(pages, 1) })}</span>
        <Button size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          {t('common.next')}
        </Button>
      </div>
    </div>
  );
}
