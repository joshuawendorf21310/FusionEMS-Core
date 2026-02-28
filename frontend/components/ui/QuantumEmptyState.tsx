'use client';

import * as React from 'react';
import { clsx } from 'clsx';

export interface QuantumEmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function QuantumEmptyState({
  icon,
  title,
  description,
  action,
  className,
}: QuantumEmptyStateProps) {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center py-16 px-6 text-center',
        className,
      )}
    >
      {icon && (
        <div className="mb-4 text-text-muted opacity-60" aria-hidden="true">
          {icon}
        </div>
      )}
      <h3
        className="font-label text-h3 font-semibold text-text-primary mb-2"
      >
        {title}
      </h3>
      {description && (
        <p className="text-body text-text-muted max-w-md mb-6">
          {description}
        </p>
      )}
      {action && <div>{action}</div>}
    </div>
  );
}
