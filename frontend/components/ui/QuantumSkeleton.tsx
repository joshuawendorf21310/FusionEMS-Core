'use client';

import * as React from 'react';
import { clsx } from 'clsx';

export interface QuantumSkeletonProps {
  className?: string;
  variant?: 'line' | 'rect' | 'circle';
  width?: string | number;
  height?: string | number;
  count?: number;
}

function SkeletonPrimitive({
  className,
  variant = 'line',
  width,
  height,
}: Omit<QuantumSkeletonProps, 'count'>) {
  const baseClass = 'animate-pulse bg-bg-overlay';
  const variantClass = {
    line: 'h-4 rounded chamfer-4',
    rect: 'rounded chamfer-8',
    circle: 'rounded-full',
  }[variant];

  return (
    <div
      className={clsx(baseClass, variantClass, className)}
      style={{
        width: width ?? (variant === 'circle' ? 40 : '100%'),
        height: height ?? (variant === 'line' ? 16 : variant === 'circle' ? 40 : 120),
      }}
      aria-hidden="true"
    />
  );
}

export function QuantumSkeleton({
  count = 1,
  ...props
}: QuantumSkeletonProps) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <SkeletonPrimitive key={i} {...props} />
      ))}
    </>
  );
}

export function QuantumCardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        'bg-bg-panel border border-border-DEFAULT chamfer-8 p-4 space-y-3',
        className,
      )}
    >
      <QuantumSkeleton variant="line" width="40%" height={12} />
      <QuantumSkeleton variant="line" width="100%" height={28} />
      <QuantumSkeleton variant="line" width="60%" height={10} />
    </div>
  );
}

export function QuantumTableSkeleton({
  rows = 5,
  cols = 4,
  className,
}: {
  rows?: number;
  cols?: number;
  className?: string;
}) {
  return (
    <div className={clsx('space-y-2', className)}>
      <div className="flex gap-4 pb-2 border-b border-border-DEFAULT">
        {Array.from({ length: cols }, (_, i) => (
          <QuantumSkeleton key={i} variant="line" width={`${100 / cols}%`} height={12} />
        ))}
      </div>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="flex gap-4 py-2">
          {Array.from({ length: cols }, (_, c) => (
            <QuantumSkeleton key={c} variant="line" width={`${100 / cols}%`} height={14} />
          ))}
        </div>
      ))}
    </div>
  );
}
