'use client';

import * as React from 'react';
import { clsx } from 'clsx';

export interface QuantumHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  breadcrumb?: React.ReactNode;
  className?: string;
}

export function QuantumHeader({
  title,
  subtitle,
  actions,
  breadcrumb,
  className,
}: QuantumHeaderProps) {
  return (
    <div
      className={clsx(
        'hud-rail flex flex-col gap-1 pb-4 mb-6 border-b border-border-DEFAULT',
        className,
      )}
    >
      {breadcrumb && (
        <div className="micro-caps mb-1">{breadcrumb}</div>
      )}
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-h1 font-bold text-text-primary truncate">
            {title}
          </h1>
          {subtitle && (
            <p className="text-body text-text-muted mt-1">{subtitle}</p>
          )}
        </div>
        {actions && (
          <div className="flex items-center gap-3 shrink-0">{actions}</div>
        )}
      </div>
    </div>
  );
}
