import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { cn } from '@/lib/utils';

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

interface DialogContentProps extends Omit<React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>, 'title'> {
  title: React.ReactNode;
  description?: React.ReactNode;
  footer?: React.ReactNode;
}

export function DialogContent({ title, description, footer, children, className, ...props }: DialogContentProps): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-overlay" />
      <div className="pointer-events-none fixed inset-0 z-50 grid place-items-center p-4">
        <DialogPrimitive.Content
          className={cn(
            'pointer-events-auto flex max-h-[calc(100%-32px)] w-full max-w-[640px] flex-col rounded-dialog border border-line bg-panel shadow-[0_12px_36px_var(--color-shadow)]',
            className,
          )}
          {...props}
        >
          <div className="flex items-center justify-between gap-2 border-b border-line2 px-4.5 py-3.5">
            <DialogPrimitive.Title className="font-head text-lg font-semibold">{title}</DialogPrimitive.Title>
            <DialogPrimitive.Close
              className="inline-grid size-8 cursor-pointer place-items-center rounded-full border border-line bg-panel text-muted hover:text-ink"
              aria-label={t('common.close')}
            >
              <X className="size-4" aria-hidden="true" />
            </DialogPrimitive.Close>
          </div>
          <div className="flex flex-col gap-3.5 overflow-auto px-4.5 py-4">
            {description ? (
              <DialogPrimitive.Description className="m-0 text-muted">{description}</DialogPrimitive.Description>
            ) : (
              <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>
            )}
            {children}
          </div>
          {footer ? (
            <div className="flex flex-wrap justify-end gap-2 border-t border-line2 px-4.5 py-3">{footer}</div>
          ) : null}
        </DialogPrimitive.Content>
      </div>
    </DialogPrimitive.Portal>
  );
}
