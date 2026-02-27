'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const FIELD_STYLE: React.CSSProperties = {
  width: '100%',
  background: 'var(--color-bg-input)',
  border: '1px solid var(--color-border-default)',
  color: 'var(--color-text-primary)',
  fontSize: 'var(--text-body)',
  padding: '10px 14px',
  outline: 'none',
  clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)',
};

const LABEL_STYLE: React.CSSProperties = {
  display: 'block',
  fontFamily: 'var(--font-label)',
  fontSize: 'var(--text-label)',
  fontWeight: 600,
  letterSpacing: 'var(--tracking-label)',
  textTransform: 'uppercase',
  color: 'var(--color-text-muted)',
  marginBottom: 6,
};

export default function PatientLookupPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    firstName: '',
    lastName: '',
    dob: '',
    ssn4: '',
    zip: '',
  });
  const [loading, setLoading] = useState(false);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      router.push('/portal/patient/statements');
    }, 1400);
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--color-bg-base)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px',
      }}
    >
      <div style={{ width: '100%', maxWidth: 480 }}>
        {/* Logo / Brand */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 48,
              height: 48,
              background: 'var(--color-brand-orange)',
              clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)',
              fontWeight: 900,
              fontSize: 14,
              color: '#000',
              marginBottom: 16,
            }}
          >
            FQ
          </div>
          <div
            style={{
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-micro)',
              fontWeight: 600,
              letterSpacing: 'var(--tracking-micro)',
              textTransform: 'uppercase',
              color: 'var(--color-brand-orange)',
              marginBottom: 8,
            }}
          >
            FusionEMS Quantum
          </div>
          <h1
            style={{
              fontSize: 'var(--text-h2)',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              lineHeight: 'var(--leading-tight)',
              marginBottom: 8,
            }}
          >
            Find Your Account
          </h1>
          <p
            style={{
              fontSize: 'var(--text-body)',
              color: 'var(--color-text-muted)',
            }}
          >
            Enter your information to access your billing account
          </p>
        </div>

        {/* Form card */}
        <div
          style={{
            background: 'var(--color-bg-panel)',
            border: '1px solid var(--color-border-default)',
            clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
            padding: 28,
          }}
        >
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 14,
              }}
            >
              <div>
                <label style={LABEL_STYLE} htmlFor="firstName">First Name</label>
                <input
                  id="firstName"
                  name="firstName"
                  type="text"
                  required
                  autoComplete="given-name"
                  value={form.firstName}
                  onChange={handleChange}
                  style={FIELD_STYLE}
                  placeholder="Jane"
                />
              </div>
              <div>
                <label style={LABEL_STYLE} htmlFor="lastName">Last Name</label>
                <input
                  id="lastName"
                  name="lastName"
                  type="text"
                  required
                  autoComplete="family-name"
                  value={form.lastName}
                  onChange={handleChange}
                  style={FIELD_STYLE}
                  placeholder="Doe"
                />
              </div>
            </div>

            <div>
              <label style={LABEL_STYLE} htmlFor="dob">Date of Birth</label>
              <input
                id="dob"
                name="dob"
                type="date"
                required
                value={form.dob}
                onChange={handleChange}
                style={FIELD_STYLE}
              />
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 14,
              }}
            >
              <div>
                <label style={LABEL_STYLE} htmlFor="ssn4">Last 4 of SSN</label>
                <input
                  id="ssn4"
                  name="ssn4"
                  type="password"
                  required
                  maxLength={4}
                  inputMode="numeric"
                  pattern="\d{4}"
                  value={form.ssn4}
                  onChange={handleChange}
                  style={FIELD_STYLE}
                  placeholder="••••"
                />
              </div>
              <div>
                <label style={LABEL_STYLE} htmlFor="zip">ZIP Code</label>
                <input
                  id="zip"
                  name="zip"
                  type="text"
                  required
                  maxLength={10}
                  inputMode="numeric"
                  value={form.zip}
                  onChange={handleChange}
                  style={FIELD_STYLE}
                  placeholder="90210"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: 6,
                background: loading ? 'var(--color-brand-orange-dim)' : 'var(--color-brand-orange)',
                color: '#000',
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-label)',
                fontWeight: 700,
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
                border: 'none',
                padding: '13px 20px',
                cursor: loading ? 'not-allowed' : 'pointer',
                clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              {loading ? (
                <>
                  <span
                    style={{
                      width: 14,
                      height: 14,
                      border: '2px solid rgba(0,0,0,0.3)',
                      borderTopColor: '#000',
                      borderRadius: '50%',
                      display: 'inline-block',
                      animation: 'spin 0.7s linear infinite',
                    }}
                  />
                  Searching...
                </>
              ) : (
                'Find My Account'
              )}
            </button>
          </form>
        </div>

        {/* Privacy notice */}
        <div
          style={{
            marginTop: 20,
            padding: '12px 16px',
            background: 'rgba(34, 211, 238, 0.05)',
            border: '1px solid rgba(34, 211, 238, 0.12)',
            clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)',
          }}
        >
          <p
            style={{
              fontSize: 11,
              color: 'var(--color-text-muted)',
              lineHeight: 'var(--leading-base)',
              textAlign: 'center',
            }}
          >
            Your information is encrypted and protected under HIPAA. We will never share your data.
          </p>
        </div>

        {/* Back link */}
        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <Link
            href="/portal/patient"
            style={{
              fontSize: 'var(--text-body)',
              color: 'var(--color-text-muted)',
              textDecoration: 'none',
            }}
          >
            ← Return to Patient Portal
          </Link>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        input:focus { border-color: var(--color-border-focus) !important; }
      `}</style>
    </div>
  );
}
