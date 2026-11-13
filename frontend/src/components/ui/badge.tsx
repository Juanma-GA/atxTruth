import { cva, type VariantProps } from 'class-variance-authority';
import * as React from 'react';

import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1 whitespace-nowrap rounded-full border border-transparent px-2 py-px text-[11.5px] font-semibold',
  {
    variants: {
      tone: {
        ok: 'bg-ok-soft text-ok',
        warn: 'bg-warn-soft text-warn',
        bad: 'bg-bad-soft text-bad',
        info: 'bg-accent-soft text-accent',
        plain: 'border-line text-muted',
      },
    },
    defaultVariants: { tone: 'plain' },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps): React.JSX.Element {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
