import * as TabsPrimitive from '@radix-ui/react-tabs';
import * as React from 'react';

import { cn } from '@/lib/utils';

export const Tabs = TabsPrimitive.Root;
export const TabsContent = TabsPrimitive.Content;

export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List ref={ref} className={cn('flex flex-wrap gap-0.5 border-b border-line', className)} {...props} />
));
TabsList.displayName = 'TabsList';

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      '-mb-px inline-flex min-h-9 cursor-pointer items-center gap-1.5 border-0 border-b-2 border-transparent bg-transparent px-3 py-2 font-medium data-[state=active]:border-accent data-[state=active]:text-accent',
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = 'TabsTrigger';
