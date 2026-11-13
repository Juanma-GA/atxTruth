import * as React from 'react';

import { cn } from '@/lib/utils';

export const Card = React.forwardRef<HTMLElement, React.HTMLAttributes<HTMLElement>>(({ className, ...props }, ref) => (
  <section ref={ref} className={cn('rounded-base border border-line bg-panel', className)} {...props} />
));
Card.displayName = 'Card';

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>): React.JSX.Element {
  return (
    <div
      className={cn('flex flex-wrap items-center justify-between gap-2 border-b border-line2 px-3.5 py-2.5', className)}
      {...props}
    />
  );
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>): React.JSX.Element {
  return <h3 className={cn('text-[15px]', className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>): React.JSX.Element {
  return <div className={cn('p-3.5', className)} {...props} />;
}
