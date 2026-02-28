'use client';

import { ReactNode } from 'react';
import { usePathname } from 'next/navigation';

const STEPS = [
  { label: 'Agency Info', path: '/signup' },
  { label: 'Legal',       path: '/signup/legal' },
  { label: 'Checkout',    path: '/signup/checkout' },
  { label: 'Done',        path: '/signup/success' },
];

function HexLogo() {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon
        points="18,2 33,10 33,26 18,34 3,26 3,10"
        fill="var(--color-brand-orange)"
        stroke="var(--color-brand-orange)"
        strokeWidth="1"
      />
      <text
        x="18"
        y="23"
        textAnchor="middle"
        fill="black"
        fontSize="13"
        fontWeight="900"
        fontFamily="'Barlow Condensed', 'Barlow', sans-serif"
        letterSpacing="0.5"
      >
        FQ
      </text>
    </svg>
  );
}

function StepIndicator({ pathname }: { pathname: string }) {
  const currentIndex = STEPS.reduce((found, step, idx) => {
    if (pathname === step.path || pathname.startsWith(step.path + '/')) return idx;
    return found;
  }, 0);

  return (
    <div className="flex items-center gap-0 mt-6 mb-8">
      {STEPS.map((step, idx) => {
        const isActive    = idx === currentIndex;
        const isCompleted = idx < currentIndex;
        const isLast      = idx === STEPS.length - 1;

        return (
          <div key={step.path} className="flex items-center">
            {/* Step pill */}
            <div className="flex flex-col items-center">
              <div
                className="flex items-center justify-center rounded-sm text-xs font-bold px-3 py-1 transition-colors"
                style={{
                  backgroundColor: isActive
                    ? 'var(--color-brand-orange)'
                    : isCompleted
                    ? 'rgba(255,107,26,0.2)'
                    : 'rgba(255,255,255,0.05)',
                  color: isActive
                    ? '#000'
                    : isCompleted
                    ? 'var(--color-brand-orange)'
                    : 'rgba(255,255,255,0.35)',
                  border: isActive
                    ? '1px solid var(--color-brand-orange)'
                    : isCompleted
                    ? '1px solid rgba(255,107,26,0.4)'
                    : '1px solid rgba(255,255,255,0.08)',
                  minWidth: '90px',
                  textAlign: 'center',
                }}
              >
                {isCompleted && (
                  <svg
                    className="inline mr-1"
                    width="10"
                    height="10"
                    viewBox="0 0 10 10"
                    fill="none"
                  >
                    <path
                      d="M1.5 5l2.5 2.5 4.5-4.5"
                      stroke="var(--color-brand-orange)"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
                {step.label}
              </div>
            </div>
            {/* Connector */}
            {!isLast && (
              <div
                className="mx-1"
                style={{
                  width: '28px',
                  height: '1px',
                  backgroundColor: isCompleted
                    ? 'rgba(255,107,26,0.4)'
                    : 'rgba(255,255,255,0.08)',
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function SignupLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div
      className="min-h-screen flex flex-col items-center px-4 py-10"
      style={{ backgroundColor: 'var(--color-bg-void)' }}
    >
      {/* Logo */}
      <div className="flex flex-col items-center">
        <div className="flex items-center gap-3">
          <HexLogo />
          <div>
            <div
              className="text-text-primary font-bold tracking-wide"
              style={{
                fontFamily: "'Barlow Condensed', 'Barlow', sans-serif",
                fontSize: '20px',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              FusionEMS{' '}
              <span style={{ color: 'var(--q-orange)' }}>Quantum</span>
            </div>
            <div
              className="text-xs"
              style={{ color: 'rgba(255,255,255,0.35)', letterSpacing: '0.12em' }}
            >
              AGENCY SIGN-UP
            </div>
          </div>
        </div>
        <StepIndicator pathname={pathname} />
      </div>

      {/* Page content */}
      <div className="w-full max-w-2xl">{children}</div>

      {/* Footer */}
      <div
        className="mt-12 text-center text-xs"
        style={{ color: 'rgba(255,255,255,0.2)' }}
      >
        &copy; {new Date().getFullYear()} FusionEMS Quantum &mdash; All rights reserved.
        &nbsp;|&nbsp;
        <a
          href="/privacy"
          className="hover:text-text-primary transition-colors"
          style={{ color: 'rgba(255,255,255,0.3)' }}
        >
          Privacy
        </a>
        &nbsp;|&nbsp;
        <a
          href="/terms"
          className="hover:text-text-primary transition-colors"
          style={{ color: 'rgba(255,255,255,0.3)' }}
        >
          Terms
        </a>
      </div>
    </div>
  );
}
