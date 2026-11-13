import * as React from 'react';

import { cn } from '@/lib/utils';

export function TableWrap({ className, ...props }: React.HTMLAttributes<HTMLDivElement>): React.JSX.Element {
  return <div className={cn('max-w-full overflow-x-auto', className)} {...props} />;
}

export function Table({ className, ...props }: React.TableHTMLAttributes<HTMLTableElement>): React.JSX.Element {
  return <table className={cn('w-full border-collapse text-[13px]', className)} {...props} />;
}

export function Th({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>): React.JSX.Element {
  return (
    <th
      className={cn('whitespace-nowrap border-b border-line bg-sunk px-2.5 py-1.5 text-left text-xs font-semibold text-muted', className)}
      {...props}
    />
  );
}

export function Td({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>): React.JSX.Element {
  return <td className={cn('border-b border-line2 px-2.5 py-1.5 align-top', className)} {...props} />;
}
