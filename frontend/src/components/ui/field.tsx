import * as React from 'react';

import { cn } from '@/lib/utils';

import { Label } from './label';

interface FieldProps {
  id: string;
  label: React.ReactNode;
  hint?: React.ReactNode;
  error?: string | undefined;
  className?: string;
  children: React.ReactElement<{ id?: string; 'aria-invalid'?: boolean; 'aria-describedby'?: string }>;
}

/** Label + control + hint/error, wired with ids for screen readers. */
export function Field({ id, label, hint, error, className, children }: FieldProps): React.JSX.Element {
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean).join(' ') || undefined;
  return (
    <div className={cn('flex min-w-0 flex-col gap-1', className)}>
      <Label htmlFor={id}>{label}</Label>
      {React.cloneElement(children, { id, 'aria-invalid': Boolean(error), 'aria-describedby': describedBy })}
      {hint && !error ? (
        <p id={`${id}-hint`} className="text-xs text-muted">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-xs font-medium text-bad">
          {error}
        </p>
      ) : null}
    </div>
  );
}
