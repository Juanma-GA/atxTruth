import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import * as React from 'react';

import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-base border font-medium cursor-pointer transition-colors disabled:cursor-not-allowed disabled:opacity-45 [&_svg]:size-[15px] [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default: 'border-line bg-panel hover:border-muted',
        primary: 'border-accent bg-accent text-accent-ink hover:brightness-110',
        ghost: 'border-transparent bg-transparent hover:bg-sunk',
        danger: 'border-bad bg-bad text-panel hover:brightness-110',
        dangerOutline: 'border-line bg-panel text-bad hover:border-bad',
      },
      size: {
        default: 'min-h-control px-3 py-1.5 text-[13px]',
        sm: 'min-h-7 px-2.5 py-0.5 text-[12.5px]',
        icon: 'size-8 rounded-full p-0 text-muted hover:text-ink',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, type, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...(asChild ? {} : { type: type ?? 'button' })}
        {...props}
      />
    );
  },
);
Button.displayName = 'Button';
