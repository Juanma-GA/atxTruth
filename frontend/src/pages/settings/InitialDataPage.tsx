import { Upload } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ImportDialog } from '@/components/excel/ExcelActions';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { queryKeys } from '@/services/queryKeys';

/** Settings → Initial data (admin): the CS_Reference_Template adapter through the usual two phases. */
export function InitialDataPage(): React.JSX.Element {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <Card>
      <CardContent className="flex flex-col items-start gap-3">
        <h2 className="m-0 text-[17px]">{t('initialData.title')}</h2>
        <p className="m-0 max-w-[70ch] text-muted">{t('initialData.description')}</p>
        <Button variant="primary" onClick={() => setOpen(true)}>
          <Upload aria-hidden="true" />
          {t('initialData.button')}
        </Button>
        <ImportDialog
          open={open}
          onOpenChange={setOpen}
          base="/api/initial-load"
          what={t('excel.domains.initial_load')}
          invalidate={[queryKeys.valueListsAll, ['valueList'], queryKeys.catalogueAll]}
        />
      </CardContent>
    </Card>
  );
}
