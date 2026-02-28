'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';

const chipVariants = cva(
  [
    'inline-flex items-center gap-1.5',
    'font-label uppercase',
    'chamfer-4',
    'transition-colors duration-fast ease-out',
  ],
  {
    variants: {
      status: {
        active: [
          'bg-[rgba(34,197,94,0.12)] text-status-active',
          'border border-[rgba(34,197,94,0.25)]',
        ],
        warning: [
          'bg-[rgba(245,158,11,0.12)] text-status-warning',
          'border border-[rgba(245,158,11,0.25)]',
        ],
        critical: [
          'bg-red-ghost text-red',
          'border border-[rgba(255,45,45,0.35)]',
        ],
        info: [
          'bg-[rgba(56,189,248,0.12)] text-status-info',
          'border border-[rgba(56,189,248,0.25)]',
        ],
        neutral: [
          'bg-[rgba(255,255,255,0.04)] text-text-muted',
          'border border-border-subtle',
        ],
      },
      size: {
        sm: ['h-5 px-2 text-[var(--text-micro)] tracking-[var(--tracking-micro)]'],
        md: ['h-6 px-2.5 text-[var(--text-label)] tracking-[var(--tracking-label)]'],
        lg: ['h-7 px-3 text-[var(--text-body)] tracking-[var(--tracking-label)]'],
      },
    },
    defaultVariants: {
      status: 'neutral',
      size: 'md',
    },
  }
);

const dotColors: Record<StatusVariant, string> = {
  active:   'var(--color-status-active)',
  warning:  'var(--color-status-warning)',
  critical: 'var(--color-brand-red)',
  info:     'var(--color-status-info)',
  neutral:  'var(--color-status-neutral)',
};

type StatusVariant = 'active' | 'warning' | 'critical' | 'info' | 'neutral';

export interface StatusChipProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof chipVariants> {
  status?: StatusVariant;
  pulse?: boolean;
  dot?: boolean;
  icon?: React.ReactNode;
}

export const StatusChip = React.forwardRef<HTMLSpanElement, StatusChipProps>(
  (
    {
      className,
      status = 'neutral',
      size,
      pulse = false,
      dot = true,
      icon,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={clsx(chipVariants({ status, size }), className)}
        {...props}
      >
        {icon ? (
          <span className="shrink-0 leading-none" aria-hidden="true">
            {icon}
          </span>
        ) : dot ? (
          <span
            aria-hidden="true"
            className={clsx(
              'shrink-0 rounded-full',
              pulse && 'animate-status-pulse'
            )}
            style={{
              width: 6,
              height: 6,
              backgroundColor: dotColors[status],
            }}
          />
        ) : null}
        {children}
      </span>
    );
  }
);

StatusChip.displayName = 'StatusChip';

const UNIT_STATUS_MAP: Record<
  string,
  { status: StatusVariant; label: string }
> = {
  available:   { status: 'active',   label: 'Available'   },
  dispatched:  { status: 'info',     label: 'Dispatched'  },
  on_scene:    { status: 'warning',  label: 'On Scene'    },
  transporting:{ status: 'warning',  label: 'Transporting'},
  at_hospital: { status: 'info',     label: 'At Hospital' },
  oos:         { status: 'critical', label: 'OOS'         },
  standby:     { status: 'neutral',  label: 'Standby'     },
};

export interface UnitStatusChipProps
  extends Omit<StatusChipProps, 'status'> {
  disposition: string;
}

export function UnitStatusChip({
  disposition,
  children,
  ...props
}: UnitStatusChipProps) {
  const mapped = UNIT_STATUS_MAP[disposition.toLowerCase()] ?? {
    status: 'neutral' as StatusVariant,
    label: disposition,
  };
  return (
    <StatusChip status={mapped.status} pulse={mapped.status === 'critical'} {...props}>
      {children ?? mapped.label}
    </StatusChip>
  );
}

const CLAIM_STATUS_MAP: Record<
  string,
  { status: StatusVariant; label: string }
> = {
  clean:    { status: 'active',   label: 'Clean'    },
  pending:  { status: 'warning',  label: 'Pending'  },
  denied:   { status: 'critical', label: 'Denied'   },
  appealed: { status: 'info',     label: 'Appealed' },
  paid:     { status: 'active',   label: 'Paid'     },
  voided:   { status: 'neutral',  label: 'Voided'   },
};

export interface ClaimStatusChipProps
  extends Omit<StatusChipProps, 'status'> {
  claimStatus: string;
}

export function ClaimStatusChip({
  claimStatus,
  children,
  ...props
}: ClaimStatusChipProps) {
  const mapped = CLAIM_STATUS_MAP[claimStatus.toLowerCase()] ?? {
    status: 'neutral' as StatusVariant,
    label: claimStatus,
  };
  return (
    <StatusChip status={mapped.status} {...props}>
      {children ?? mapped.label}
    </StatusChip>
  );
}
