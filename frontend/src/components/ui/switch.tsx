import * as React from 'react';

import { cn } from '@/lib/utils';

interface SwitchProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onChange'> {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

export function Switch({ checked, onCheckedChange, className, ...props }: SwitchProps): React.JSX.Element {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-10 shrink-0 cursor-pointer items-center rounded-full border border-line transition-colors',
        checked ? 'bg-accent' : 'bg-sunk',
        className,
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className={cn(
          'inline-block size-4 rounded-full bg-panel shadow transition-transform',
          checked ? 'translate-x-5' : 'translate-x-1',
        )}
      />
    </button>
  );
}
