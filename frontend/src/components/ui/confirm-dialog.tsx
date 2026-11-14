import { useTranslation } from 'react-i18next';

import { Button } from './button';
import { Dialog, DialogContent } from './dialog';

interface Props {
  open: boolean;
  title: string;
  body: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

/** Explicit confirmation before a delete (HR9). */
export function ConfirmDialog({ open, title, body, confirmLabel, onConfirm, onCancel, danger = true }: Props): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent
        title={title}
        description={body}
        footer={
          <>
            <Button onClick={onCancel}>{t('common.cancel')}</Button>
            <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm}>
              {confirmLabel}
            </Button>
          </>
        }
      />
    </Dialog>
  );
}
