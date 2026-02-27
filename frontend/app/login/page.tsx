'use client';

import React, { useState, useCallback } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { login } from '@/services/auth';

type TabKey = 'staff' | 'billing';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'staff',   label: 'Staff Login'    },
  { key: 'billing', label: 'Billing Portal' },
];

export default function LoginPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('staff');
  const [email, setEmail]         = useState('');
  const [password, setPassword]   = useState('');
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

  const handleTabChange = useCallback((key: TabKey) => {
    setActiveTab(key);
    setError('');
    setEmail('');
    setPassword('');
  }, []);

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
        login(email.trim());
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
          borderColor:     'var(--color-border-default)',
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
                color:           'var(--color-text-inverse)',
                fontFamily:      'var(--font-label)',
                fontSize:        'var(--text-label)',
                fontWeight:      700,
                letterSpacing:   'var(--tracking-label)',
              }}
            >
              FQ
            </div>
            <span
              style={{
                fontFamily:    'var(--font-label)',
                fontSize:      'var(--text-h3)',
                fontWeight:    700,
                letterSpacing: '0.04em',
                color:         'var(--color-text-primary)',
                textTransform: 'uppercase',
              }}
            >
              FusionEMS Quantum
            </span>
          </div>
          <p className="micro-caps mt-1" style={{ color: 'var(--color-text-muted)' }}>
            Billing-first infrastructure OS
          </p>
        </div>

        {/* Tab switcher */}
        <div className="px-6 pt-5">
          <div
            className="chamfer-4 flex p-0.5"
            style={{
              backgroundColor: 'var(--color-bg-input)',
              border:          '1px solid var(--color-border-subtle)',
            }}
          >
            {TABS.map((tab) => {
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => handleTabChange(tab.key)}
                  className="relative flex-1 py-2 transition-all duration-[150ms]"
                  style={{
                    fontFamily:    'var(--font-label)',
                    fontSize:      'var(--text-label)',
                    fontWeight:    600,
                    letterSpacing: 'var(--tracking-label)',
                    textTransform: 'uppercase',
                    color:         isActive
                      ? 'var(--color-text-primary)'
                      : 'var(--color-text-muted)',
                    backgroundColor: isActive
                      ? 'var(--color-bg-panel-raised)'
                      : 'transparent',
                    clipPath: 'var(--chamfer-4)',
                    outline: 'none',
                  }}
                >
                  {tab.label}
                  {/* Orange underline on active */}
                  {isActive && (
                    <span
                      aria-hidden="true"
                      className="absolute bottom-0 left-0 right-0"
                      style={{
                        height:          2,
                        backgroundColor: 'var(--color-brand-orange)',
                      }}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 px-6 pb-6 pt-5"
          noValidate
        >
          <Input
            label={activeTab === 'staff' ? 'Staff Email' : 'Billing Email'}
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
            autoComplete={activeTab === 'staff' ? 'current-password' : 'current-password'}
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

          <div className="flex justify-center">
            <button
              type="button"
              className="chamfer-4 px-2 py-1 transition-colors duration-[150ms]"
              style={{
                fontFamily:    'var(--font-label)',
                fontSize:      'var(--text-label)',
                fontWeight:    500,
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
                color:         'var(--color-text-muted)',
                background:    'transparent',
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.color = 'var(--color-text-secondary)')
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.color = 'var(--color-text-muted)')
              }
              disabled={loading}
            >
              Forgot password?
            </button>
          </div>
        </form>

        {/* Footer */}
        <div
          className="flex items-center justify-center gap-2 px-6 py-4"
          style={{ borderTop: '1px solid var(--color-border-subtle)' }}
        >
          <svg
            aria-hidden="true"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ color: 'var(--color-text-muted)', flexShrink: 0 }}
          >
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <span
            className="micro-caps"
            style={{ color: 'var(--color-text-muted)' }}
          >
            Protected by end-to-end encryption
          </span>
        </div>
      </div>
    </div>
  );
}
