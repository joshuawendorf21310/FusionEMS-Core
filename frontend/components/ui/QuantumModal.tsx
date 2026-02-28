'use client';

import * as React from 'react';
import { clsx } from 'clsx';

export interface QuantumModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function QuantumModal({
  open,
  onClose,
  title,
  children,
  footer,
  size = 'md',
  className,
}: QuantumModalProps) {
  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  const sizeClass = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
  }[size];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={clsx(
          'relative z-10 w-full mx-4',
          sizeClass,
          'bg-bg-panel border border-border-DEFAULT',
          'shadow-elevation-4 chamfer-12',
          'animate-fade-in',
          className,
        )}
      >
        {title && (
          <div className="hud-rail flex items-center justify-between px-5 py-4 border-b border-border-DEFAULT">
            <h2 className="label-caps">{title}</h2>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-text-primary transition-colors duration-fast p-1"
              aria-label="Close"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M4 4l8 8M12 4l-8 8" />
              </svg>
            </button>
          </div>
        )}
        <div className="p-5">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-border-DEFAULT">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
