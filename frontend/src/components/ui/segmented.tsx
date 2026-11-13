import * as React from 'react';

import { cn } from '@/lib/utils';

export interface SegmentedOption<T extends string> {
  value: T;
  label: React.ReactNode;
  ariaLabel?: string;
}

interface SegmentedProps<T extends string> {
  label: string;
  value: T;
  options: SegmentedOption<T>[];
  onChange: (value: T) => void;
  className?: string;
}

/** Group of toggle buttons (aria-pressed), as in the mockup's language switch. */
export function Segmented<T extends string>({ label, value, options, onChange, className }: SegmentedProps<T>): React.JSX.Element {
  return (
    <div role="group" aria-label={label} className={cn('inline-flex overflow-hidden rounded-base border border-line', className)}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={option.value === value}
          aria-label={option.ariaLabel}
          title={option.ariaLabel}
          onClick={() => onChange(option.value)}
          className="inline-flex min-h-8 cursor-pointer items-center gap-1 border-0 bg-transparent px-2.5 py-1 text-[12.5px] font-medium aria-pressed:bg-accent aria-pressed:text-accent-ink [&_svg]:size-[15px]"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
