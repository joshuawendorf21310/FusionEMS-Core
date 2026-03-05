'use client';

import React, { useState } from 'react';
import { login } from '@/services/auth';

export default function BillingLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email.trim(), password, { redirectTo: '/billing/dashboard' });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Authentication failed';
      setError(msg);
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--color-bg-void)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        color: 'var(--color-text-primary)',
        fontFamily: 'var(--font-sans)',
      }}
    >
      {/* PHI Warning Banner */}
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          marginBottom: '24px',
          background: 'rgba(255, 107, 26, 0.08)',
          borderLeft: '4px solid var(--color-brand-orange)',
          clipPath: 'var(--chamfer-8)',
          padding: '12px 16px',
        }}
      >
        <p
          style={{
            margin: 0,
            fontSize: 'var(--text-body)',
            color: 'var(--color-text-secondary)',
            lineHeight: 'var(--leading-base)',
          }}
        >
          This system contains PHI. Unauthorized access is prohibited.
        </p>
      </div>

      {/* Login Card */}
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          background: 'var(--color-bg-panel)',
          clipPath: 'var(--chamfer-8)',
          padding: '40px',
          boxShadow: 'var(--elevation-3)',
          borderTop: '2px solid var(--color-system-billing)',
        }}
      >
        {/* Header */}
        <div style={{ marginBottom: '32px', textAlign: 'center' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '48px',
              height: '48px',
              background: 'var(--color-bg-panel-raised)',
              clipPath: 'var(--chamfer-8)',
              marginBottom: '16px',
              fontWeight: 700,
              fontSize: '14px',
              color: 'var(--color-system-billing)',
              fontFamily: 'var(--font-label)',
              letterSpacing: 'var(--tracking-label)',
            }}
          >
            FQ
          </div>
          <h1
            style={{
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-h2)',
              fontWeight: 700,
              letterSpacing: 'var(--tracking-label)',
              textTransform: 'uppercase',
              color: 'var(--color-text-primary)',
              margin: '0 0 8px 0',
            }}
          >
            FusionEMS Billing Portal
          </h1>
          <p
            style={{
              fontSize: 'var(--text-body)',
              color: 'var(--color-text-muted)',
              margin: 0,
              lineHeight: 'var(--leading-base)',
            }}
          >
            Authorized billing staff only — access is monitored and logged
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Email */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label
              htmlFor="email"
              style={{
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-label)',
                fontWeight: 600,
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
                color: 'var(--color-text-secondary)',
              }}
            >
              Email Address
            </label>
            <div
              style={{
                background: 'var(--color-bg-input)',
                clipPath: 'var(--chamfer-8)',
                border: '1px solid var(--color-border-default)',
                padding: '0 12px',
                display: 'flex',
                alignItems: 'center',
                height: 'var(--density-input-height)',
              }}
            >
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="billing@agency.gov"
                required
                disabled={loading}
                style={{
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-body)',
                  width: '100%',
                  fontFamily: 'var(--font-sans)',
                }}
              />
            </div>
          </div>

          {/* Password */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label
              htmlFor="password"
              style={{
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-label)',
                fontWeight: 600,
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
                color: 'var(--color-text-secondary)',
              }}
            >
              Password
            </label>
            <div
              style={{
                background: 'var(--color-bg-input)',
                clipPath: 'var(--chamfer-8)',
                border: '1px solid var(--color-border-default)',
                padding: '0 12px',
                display: 'flex',
                alignItems: 'center',
                height: 'var(--density-input-height)',
              }}
            >
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={loading}
                style={{
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-body)',
                  width: '100%',
                  fontFamily: 'var(--font-sans)',
                }}
              />
            </div>
          </div>

          {error && (
            <p
              role="alert"
              style={{
                margin: '0 0 4px 0',
                color: 'var(--color-brand-red)',
                fontSize: 'var(--text-label)',
                fontFamily: 'var(--font-label)',
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
              }}
            >
              {error}
            </p>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: '8px',
              height: 'var(--density-button-height)',
              background: 'var(--color-brand-orange)',
              clipPath: 'var(--chamfer-8)',
              border: 'none',
              color: 'rgba(0,0,0,0.92)',
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-label)',
              fontWeight: 700,
              letterSpacing: 'var(--tracking-label)',
              textTransform: 'uppercase',
              cursor: 'pointer',
              transition: 'opacity var(--duration-fast) var(--ease-out)',
              opacity: loading ? 0.75 : 1,
            }}
            onMouseEnter={(e) => {
              if (loading) return;
              (e.currentTarget as HTMLButtonElement).style.opacity = '0.88';
            }}
            onMouseLeave={(e) => {
              if (loading) return;
              (e.currentTarget as HTMLButtonElement).style.opacity = '1';
            }}
          >
            {loading ? 'Signing In…' : 'Sign In to Billing Portal'}
          </button>
        </form>

        {/* Request Access Link */}
        <div style={{ marginTop: '20px', textAlign: 'center' }}>
          <a
            href="mailto:admin@fusionems.io?subject=Billing Portal Access Request"
            style={{
              fontSize: 'var(--text-body)',
              color: 'var(--color-text-muted)',
              textDecoration: 'none',
              borderBottom: '1px solid var(--color-border-subtle)',
              paddingBottom: '1px',
              transition: 'color var(--duration-fast)',
            }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLAnchorElement).style.color =
                'var(--color-text-secondary)')
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLAnchorElement).style.color = 'var(--color-text-muted)')
            }
          >
            Request Access
          </a>
        </div>
      </div>
    </div>
  );
}
