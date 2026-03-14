'use client';

import React, { Suspense, useState, useCallback, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { login } from '@/services/auth';

function LoginPageInner() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const searchParams = useSearchParams();

  useEffect(() => {
    const ssoError = searchParams.get('error');
    if (ssoError === 'entra_denied') {
      setError('Microsoft login was denied. Contact your administrator.');
    } else if (ssoError === 'no_account') {
      setError('No FusionEMS account is linked to that Microsoft identity.');
    }
  }, [searchParams]);

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!email.trim()) {
        setError('Email address is required.');
        return;
      }
      if (!password.trim()) {
        setError('Password is required.');
        return;
      }
      setError('');
      setLoading(true);
      try {
        await login(email.trim(), password);
      } catch {
        setError('Authentication failed. Verify your credentials and try again.');
        setLoading(false);
      }
    },
    [email, password]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') handleSubmit();
    },
    [handleSubmit]
  );

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4 py-12"
      style={{ backgroundColor: 'var(--color-bg-void)' }}
    >
      {/* Login panel */}
      <div
        className="w-full max-w-md chamfer-12 border shadow-[var(--elevation-3)]"
        style={{
          backgroundColor: 'var(--color-bg-panel)',
          borderColor: 'var(--color-border-default)',
        }}
      >
        {/* Wordmark */}
        <div
          className="hud-rail flex flex-col items-center px-8 pt-8 pb-6"
          style={{ borderBottom: '1px solid var(--color-border-default)' }}
        >
          <div className="flex items-center gap-2 mb-1">
            <div
              className="chamfer-4 flex h-8 w-8 items-center justify-center"
              style={{
                backgroundColor: 'var(--color-brand-orange)',
                color: 'var(--color-text-inverse)',
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-label)',
                fontWeight: 700,
                letterSpacing: 'var(--tracking-label)',
              }}
            >
              FQ
            </div>
            <span
              style={{
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-h3)',
                fontWeight: 700,
                letterSpacing: '0.04em',
                color: 'var(--color-text-primary)',
                textTransform: 'uppercase',
              }}
            >
              FusionEMS Quantum
            </span>
          </div>
          <p className="micro-caps mt-1" style={{ color: 'var(--color-text-muted)' }}>
            Platform Login
          </p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 px-6 pb-6 pt-5"
          noValidate
        >
          <Input
            label="Email"
            type="email"
            placeholder="name@agency.gov"
            autoComplete="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); setError(''); }}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />

          <Input
            label="Password"
            type="password"
            placeholder="••••••••••••"
            autoComplete="current-password"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setError(''); }}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />

          {/* Inline error */}
          {error && (
            <p
              role="alert"
              className="micro-caps"
              style={{ color: 'var(--color-brand-red)' }}
            >
              {error}
            </p>
          )}

          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={loading}
            className="w-full mt-1"
          >
            Sign In
          </Button>

          <div className="flex items-center gap-3 py-3">
            <span
              className="flex-1"
              style={{ height: 1, backgroundColor: 'var(--color-border-subtle)' }}
            />
            <span
              className="micro-caps"
              style={{ color: 'var(--color-text-muted)' }}
            >
              or
            </span>
            <span
              className="flex-1"
              style={{ height: 1, backgroundColor: 'var(--color-border-subtle)' }}
            />
          </div>

          <a
            href={`${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/auth/microsoft/login`}
            className="chamfer-8 flex w-full items-center justify-center gap-2 py-2.5 transition-colors duration-[150ms]"
            style={{
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-label)',
              fontWeight: 600,
              letterSpacing: 'var(--tracking-label)',
              textTransform: 'uppercase',
              color: 'var(--color-text-primary)',
              backgroundColor: 'var(--color-bg-input)',
              border: '1px solid var(--color-border-default)',
              textDecoration: 'none',
            }}
          >
            <svg
              aria-hidden="true"
              width="16"
              height="16"
              viewBox="0 0 21 21"
              fill="none"
            >
              <rect x="1" y="1" width="9" height="9" fill="#F25022" />
              <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
              <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
              <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
            </svg>
            Sign in with Microsoft
          </a>

        </form>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginPageInner />
    </Suspense>
  );
}
