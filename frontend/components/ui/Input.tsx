'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';

/*
  Input — base text input for FusionEMS Quantum.
  All inputs use chamfer-4 (small controls), bg-bg-input, and the
  orange focus ring on interaction — never border-radius.

  Variants:
    - default:  standard text field
    - search:   with leading search icon
    - inline:   borderless, for table cell editing

  States:
    - default / focus / error / disabled
    - PHI mode: blurs value until user focuses (patient data protection)

  Usage:
    <Input label="Patient Name" placeholder="Last, First" />
    <Input variant="search" placeholder="Search incidents…" />
    <Input label="SSN" phi />
    <Input label="Denial Reason" error="Required field" />
*/

const inputVariants = cva(
  [
    'relative w-full',
    'font-sans text-body text-text-primary',
    'bg-bg-input',
    'border border-border-DEFAULT',
    'chamfer-4',
    'transition-all duration-fast ease-out',
    'placeholder:text-text-muted',
    'focus:outline-none focus:border-orange focus:shadow-focus',
    'disabled:opacity-40 disabled:cursor-not-allowed',
    'read-only:opacity-70 read-only:cursor-default',
  ],
  {
    variants: {
      variant: {
        default: [],
        search: ['pl-9'],
        inline: [
          'bg-transparent border-transparent',
          'focus:bg-bg-input focus:border-orange',
        ],
      },
      size: {
        sm: ['h-8 px-2.5 text-[var(--text-micro)]'],
        md: ['h-[var(--density-input-height)] px-3'],
        lg: ['h-11 px-4'],
      },
      hasError: {
        true: [
          'border-red focus:border-red',
          '!shadow-[0_0_0_2px_var(--color-bg-base),0_0_0_4px_var(--color-brand-red)]',
        ],
        false: [],
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
      hasError: false,
    },
  }
);

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'>,
    VariantProps<typeof inputVariants> {
  label?: string;
  hint?: string;
  error?: string;
  phi?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  containerClassName?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      containerClassName,
      variant,
      size,
      label,
      hint,
      error,
      phi = false,
      leftIcon,
      rightIcon,
      id: idProp,
      disabled,
      ...props
    },
    ref
  ) => {
    const generatedId = React.useId();
    const id = idProp ?? generatedId;
    const hintId = `${id}-hint`;
    const errorId = `${id}-error`;
    const hasError = Boolean(error);

    const [phiRevealed, setPhiRevealed] = React.useState(false);

    return (
      <div className={clsx('flex flex-col gap-1.5', containerClassName)}>
        {label && (
          <label htmlFor={id} className="label-caps">
            {label}
            {phi && (
              <span
                className="ml-1.5 micro-caps"
                style={{ color: 'var(--color-status-warning)' }}
                title="Protected Health Information"
              >
                PHI
              </span>
            )}
          </label>
        )}

        <div className="relative flex items-center">
          {(leftIcon || variant === 'search') && (
            <span
              className="absolute left-2.5 shrink-0 pointer-events-none"
              style={{
                color: 'var(--color-text-muted)',
                width: 'var(--density-icon-size)',
                height: 'var(--density-icon-size)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              aria-hidden="true"
            >
              {leftIcon ?? <SearchIcon />}
            </span>
          )}

          <input
            ref={ref}
            id={id}
            disabled={disabled}
            aria-describedby={
              [hint && hintId, error && errorId].filter(Boolean).join(' ') ||
              undefined
            }
            aria-invalid={hasError || undefined}
            className={clsx(
              inputVariants({ variant, size, hasError }),
              leftIcon || variant === 'search' ? 'pl-9' : undefined,
              rightIcon ? 'pr-9' : undefined,
              phi && !phiRevealed
                ? '[filter:blur(4px)] select-none focus:[filter:none]'
                : undefined,
              className
            )}
            onFocus={(e) => {
              if (phi) setPhiRevealed(true);
              props.onFocus?.(e);
            }}
            onBlur={(e) => {
              if (phi) setPhiRevealed(false);
              props.onBlur?.(e);
            }}
            {...props}
          />

          {rightIcon && (
            <span
              className="absolute right-2.5 shrink-0 pointer-events-none"
              style={{
                color: 'var(--color-text-muted)',
                width: 'var(--density-icon-size)',
                height: 'var(--density-icon-size)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              aria-hidden="true"
            >
              {rightIcon}
            </span>
          )}
        </div>

        {hint && !error && (
          <p id={hintId} className="micro-caps pl-0.5">
            {hint}
          </p>
        )}

        {error && (
          <p
            id={errorId}
            role="alert"
            className="micro-caps pl-0.5"
            style={{ color: 'var(--color-brand-red)' }}
          >
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

function SearchIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.35-4.35" />
    </svg>
  );
}

/*
  Textarea — multi-line input, same token system as Input.
*/
export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
  containerClassName?: string;
  rows?: number;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className,
      containerClassName,
      label,
      hint,
      error,
      id: idProp,
      rows = 4,
      ...props
    },
    ref
  ) => {
    const generatedId = React.useId();
    const id = idProp ?? generatedId;
    const hintId = `${id}-hint`;
    const errorId = `${id}-error`;
    const hasError = Boolean(error);

    return (
      <div className={clsx('flex flex-col gap-1.5', containerClassName)}>
        {label && (
          <label htmlFor={id} className="label-caps">
            {label}
          </label>
        )}

        <textarea
          ref={ref}
          id={id}
          rows={rows}
          aria-describedby={
            [hint && hintId, error && errorId].filter(Boolean).join(' ') ||
            undefined
          }
          aria-invalid={hasError || undefined}
          className={clsx(
            'w-full px-3 py-2.5',
            'font-sans text-body text-text-primary',
            'bg-bg-input',
            'border border-border-DEFAULT',
            'chamfer-4',
            'transition-all duration-fast ease-out',
            'placeholder:text-text-muted',
            'focus:outline-none focus:border-orange focus:shadow-focus',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            'resize-y',
            hasError && 'border-red !shadow-[0_0_0_2px_var(--color-bg-base),0_0_0_4px_var(--color-brand-red)]',
            className
          )}
          {...props}
        />

        {hint && !error && (
          <p id={hintId} className="micro-caps pl-0.5">
            {hint}
          </p>
        )}

        {error && (
          <p
            id={errorId}
            role="alert"
            className="micro-caps pl-0.5"
            style={{ color: 'var(--color-brand-red)' }}
          >
            {error}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
