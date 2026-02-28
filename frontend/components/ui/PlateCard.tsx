'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';

/*
  PlateCard — the primary surface container in FusionEMS Quantum.
  Named "plate" because it echoes the branded Wedgepoint Q identity system —
  machined panel aesthetic, chamfered corners, no border-radius.

  Three structural variants:
    - default: standard panel with chamfer-8
    - raised:  elevated modal/drawer surface with chamfer-12
    - flush:   no border, no shadow — for nested content areas

  Optional slots:
    - header: section title row with HUD tick rail
    - footer: action row at bottom of card
    - accent: left-edge accent bar (system line color)

  Usage:
    <PlateCard header="Active Incidents" accent="fire">
      ...content...
    </PlateCard>
*/

const plateVariants = cva(
  [
    'relative flex flex-col overflow-hidden',
    'transition-shadow duration-base ease-out',
  ],
  {
    variants: {
      variant: {
        default: [
          'bg-bg-panel',
          'border border-border-DEFAULT',
          'shadow-elevation-1',
          'chamfer-8',
        ],
        raised: [
          'bg-bg-raised',
          'border border-border-strong',
          'shadow-elevation-3',
          'chamfer-12',
        ],
        flush: [
          'bg-transparent',
        ],
      },
      interactive: {
        true: [
          'cursor-pointer',
          'hover:border-border-strong',
          'hover:shadow-elevation-2',
          'focus-visible:outline-none',
          'focus-visible:shadow-focus',
        ],
        false: [],
      },
      critical: {
        true: [
          'shadow-critical',
          'border-red',
        ],
        false: [],
      },
    },
    defaultVariants: {
      variant: 'default',
      interactive: false,
      critical: false,
    },
  }
);

const accentColors: Record<string, string> = {
  orange:     'var(--color-brand-orange)',
  red:        'var(--color-brand-red)',
  fire:       'var(--color-system-fire)',
  billing:    'var(--color-system-billing)',
  hems:       'var(--color-system-hems)',
  fleet:      'var(--color-system-fleet)',
  compliance: 'var(--color-system-compliance)',
  cad:        'var(--color-system-cad)',
  active:     'var(--color-status-active)',
  warning:    'var(--color-status-warning)',
  critical:   'var(--color-brand-red)',
  info:       'var(--color-status-info)',
};

export interface PlateCardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof plateVariants> {
  header?: React.ReactNode;
  headerRight?: React.ReactNode;
  footer?: React.ReactNode;
  accent?: keyof typeof accentColors | (string & {});
  accentWidth?: number;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export const PlateCard = React.forwardRef<HTMLDivElement, PlateCardProps>(
  (
    {
      className,
      variant,
      interactive,
      critical,
      header,
      headerRight,
      footer,
      accent,
      accentWidth = 3,
      padding = 'md',
      children,
      ...props
    },
    ref
  ) => {
    const accentColor = accent ? (accentColors[accent] ?? accent) : undefined;

    const paddingClass = {
      none: '',
      sm:   'p-3',
      md:   'p-4',
      lg:   'p-6',
    }[padding];

    return (
      <div
        ref={ref}
        className={clsx(
          plateVariants({ variant, interactive, critical }),
          className
        )}
        tabIndex={interactive ? 0 : undefined}
        role={interactive ? 'button' : undefined}
        {...props}
      >
        {accentColor && (
          <div
            aria-hidden="true"
            className="absolute top-0 left-0 bottom-0 z-10 pointer-events-none"
            style={{
              width: accentWidth,
              backgroundColor: accentColor,
            }}
          />
        )}

        {header && (
          <PlateCardHeader right={headerRight} accentColor={accentColor}>
            {header}
          </PlateCardHeader>
        )}

        <div
          className={clsx(
            'flex-1 min-h-0',
            paddingClass,
            accentColor && 'pl-[calc(var(--space-4)_+_3px)]'
          )}
        >
          {children}
        </div>

        {footer && (
          <PlateCardFooter>{footer}</PlateCardFooter>
        )}
      </div>
    );
  }
);

PlateCard.displayName = 'PlateCard';

interface PlateCardHeaderProps {
  right?: React.ReactNode;
  accentColor?: string;
  children: React.ReactNode;
}

function PlateCardHeader({ right, accentColor, children }: PlateCardHeaderProps) {
  return (
    <div
      className={clsx(
        'hud-rail',
        'flex items-center justify-between',
        'px-4 py-3',
        'border-b border-border-DEFAULT',
      )}
      style={accentColor ? { paddingLeft: 'calc(var(--space-4) + 3px)' } : undefined}
    >
      <div className="flex items-center gap-2 min-w-0">
        {typeof children === 'string' ? (
          <span className="label-caps truncate">{children}</span>
        ) : (
          children
        )}
      </div>
      {right && (
        <div className="flex items-center gap-2 shrink-0 ml-4">{right}</div>
      )}
    </div>
  );
}

function PlateCardFooter({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-border-DEFAULT">
      {children}
    </div>
  );
}

/*
  MetricPlate — compact stat display card used in dashboard grids.
  Shows a single KPI value with label, trend, and optional system accent.

  Usage:
    <MetricPlate
      label="Active Units"
      value="12"
      trend="+2"
      trendDirection="up"
      accent="cad"
    />
*/
export interface MetricPlateProps {
  label: string;
  value: string | number;
  trend?: string;
  trendDirection?: 'up' | 'down' | 'neutral';
  trendPositive?: boolean;
  accent?: string;
  className?: string;
}

export function MetricPlate({
  label,
  value,
  trend,
  trendDirection = 'neutral',
  trendPositive,
  accent,
  className,
}: MetricPlateProps) {
  const trendColor =
    trendPositive === undefined
      ? 'var(--color-text-muted)'
      : trendDirection === 'up'
      ? trendPositive
        ? 'var(--color-status-active)'
        : 'var(--color-brand-red)'
      : trendDirection === 'down'
      ? trendPositive
        ? 'var(--color-brand-red)'
        : 'var(--color-status-active)'
      : 'var(--color-text-muted)';

  return (
    <PlateCard
      accent={accent}
      accentWidth={3}
      padding="md"
      className={className}
    >
      <p className="label-caps mb-3">{label}</p>
      <p
        className="font-sans font-bold leading-none"
        style={{ fontSize: 'var(--text-h1)' }}
      >
        {value}
      </p>
      {trend && (
        <p
          className="micro-caps mt-2"
          style={{ color: trendColor }}
        >
          {trendDirection === 'up' ? '▲' : trendDirection === 'down' ? '▼' : '—'}{' '}
          {trend}
        </p>
      )}
    </PlateCard>
  );
}
