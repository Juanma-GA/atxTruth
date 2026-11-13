import * as React from 'react';

import { cn } from '@/lib/utils';

export const controlClass =
  'w-full min-w-0 min-h-control rounded-small border border-line bg-sunk px-2 py-1.5 aria-[invalid=true]:border-bad disabled:opacity-60';

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => <input ref={ref} className={cn(controlClass, className)} {...props} />,
);
Input.displayName = 'Input';

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea ref={ref} className={cn(controlClass, 'min-h-24 resize-y', className)} {...props} />
  ),
);
Textarea.displayName = 'Textarea';

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => <select ref={ref} className={cn(controlClass, className)} {...props} />,
);
Select.displayName = 'Select';
