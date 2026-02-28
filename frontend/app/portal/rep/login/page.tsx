'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

const PANEL_STYLE = {
  clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
  background: 'var(--color-bg-panel, #0f1720)',
  border: '1px solid rgba(255,255,255,0.08)',
};

const INPUT_STYLE: React.CSSProperties = {
  width: '100%',
  background: '#0e161f',
  border: '1px solid rgba(255,255,255,0.08)',
  clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
  color: '#fff',
  fontSize: '0.9375rem',
  padding: '10px 12px',
  outline: 'none',
};

const LABEL_STYLE: React.CSSProperties = {
  display: 'block',
  fontSize: '0.75rem',
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: 'rgba(255,255,255,0.5)',
  marginBottom: '6px',
};

const BTN_PRIMARY: React.CSSProperties = {
  clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
  background: '#ff6b1a',
  color: '#fff',
  fontWeight: 600,
  fontSize: '0.9375rem',
  padding: '11px 0',
  width: '100%',
  border: 'none',
  cursor: 'pointer',
  letterSpacing: '0.02em',
};

export default function RepLoginPage() {
  const router = useRouter();
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!phone.trim()) {
      setError('Please enter your mobile number.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/auth-rep/register`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            phone: phone.trim(),
            patient_account_id: sessionStorage.getItem('rep_patient_id') ?? '00000000-0000-0000-0000-000000000000',
            relationship: sessionStorage.getItem('rep_relationship') ?? 'self',
            full_name: sessionStorage.getItem('rep_full_name') ?? phone.trim(),
            delivery_method: 'sms',
          }),
        }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `Request failed (${res.status})`);
      }
      sessionStorage.setItem('rep_phone', phone.trim());
      router.push('/portal/rep/verify');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{ background: 'var(--color-bg-base, #0b0f14)', minHeight: '100vh' }}
      className="flex items-center justify-center px-4 py-12"
    >
      <div style={{ width: '100%', maxWidth: '440px' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '48px',
              height: '48px',
              background: 'rgba(255,107,26,0.12)',
              border: '1px solid rgba(255,107,26,0.3)',
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
              marginBottom: '18px',
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ff6b1a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <h1 style={{ color: '#fff', fontSize: '1.375rem', fontWeight: 700, margin: '0 0 8px' }}>
            Authorized Representative Portal
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.875rem', margin: 0 }}>
            Access your patient's billing account
          </p>
        </div>

        {/* Card */}
        <div style={{ ...PANEL_STYLE, padding: '28px 28px 24px' }}>
          <form onSubmit={handleSubmit} noValidate>
            <div style={{ marginBottom: '22px' }}>
              <label style={LABEL_STYLE} htmlFor="rep-phone">Your Mobile Number</label>
              <input
                id="rep-phone"
                type="tel"
                autoComplete="tel"
                placeholder="+1 (555) 000-0000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                style={INPUT_STYLE}
                disabled={loading}
              />
            </div>

            {error && (
              <div
                style={{
                  background: 'rgba(220,38,38,0.12)',
                  border: '1px solid rgba(220,38,38,0.35)',
                  clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
                  color: '#f87171',
                  fontSize: '0.8125rem',
                  padding: '10px 12px',
                  marginBottom: '16px',
                }}
              >
                {error}
              </div>
            )}

            <button type="submit" style={{ ...BTN_PRIMARY, opacity: loading ? 0.6 : 1 }} disabled={loading}>
              {loading ? 'Sending...' : 'Send Verification Code'}
            </button>
          </form>

          <p style={{ color: 'rgba(255,255,255,0.35)', fontSize: '0.75rem', textAlign: 'center', marginTop: '16px', marginBottom: 0 }}>
            A 6-digit code will be sent to your registered mobile number
          </p>
        </div>

        {/* Back link */}
        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <Link
            href="/"
            style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8125rem', textDecoration: 'none' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'rgba(255,255,255,0.7)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'rgba(255,255,255,0.4)')}
          >
            ← Back to Patient Portal
          </Link>
        </div>
      </div>
    </div>
  );
}
