import type * as React from 'react';

interface PageHeaderProps {
  title: React.ReactNode;
  description?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps): React.JSX.Element {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-[22px]">{title}</h1>
        {description ? <p className="mt-0.5 mb-0 max-w-[70ch] text-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
