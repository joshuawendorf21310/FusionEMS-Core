'use client';

import * as React from 'react';
import { clsx } from 'clsx';

export interface QuantumTableColumn<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  width?: string;
}

export interface QuantumTableProps<T> {
  columns: QuantumTableColumn<T>[];
  data: T[];
  keyField?: string;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  className?: string;
  compact?: boolean;
}

export function QuantumTable<T extends Record<string, unknown>>({
  columns,
  data,
  keyField = 'id',
  onRowClick,
  emptyMessage = 'No data available',
  className,
  compact = false,
}: QuantumTableProps<T>) {
  if (data.length === 0) {
    return (
      <div className={clsx('flex items-center justify-center py-12 text-text-muted text-body', className)}>
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className={clsx('overflow-x-auto', className)}>
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-border-DEFAULT">
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx(
                  'label-caps text-left px-[var(--density-cell-pad-x)] py-2',
                  col.align === 'center' && 'text-center',
                  col.align === 'right' && 'text-right',
                )}
                style={col.width ? { width: col.width } : undefined}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={String(row[keyField] ?? i)}
              className={clsx(
                'border-b border-border-subtle transition-colors duration-fast',
                onRowClick && 'cursor-pointer hover:bg-bg-overlay',
              )}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={clsx(
                    'px-[var(--density-cell-pad-x)]',
                    compact ? 'py-1.5' : 'py-[var(--density-cell-pad-y)]',
                    'text-body text-text-primary',
                    col.align === 'center' && 'text-center',
                    col.align === 'right' && 'text-right',
                  )}
                >
                  {col.render ? col.render(row) : String(row[col.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
