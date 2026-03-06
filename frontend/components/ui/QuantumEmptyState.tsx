'use client';

import * as React from 'react';
import { clsx } from 'clsx';

export interface QuantumEmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function QuantumEmptyState({
  icon,
  title,
  description,
  action,
  actionLabel,
  onAction,
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
      {!action && actionLabel && onAction && (
        <button
          onClick={onAction}
          className="px-4 py-2 bg-brand-orange text-white text-label rounded chamfer-4 hover:opacity-90 transition-opacity"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
