'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

const PANEL_STYLE = {
  clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
  background: 'var(--color-bg-panel, var(--color-bg-input))',
  border: '1px solid rgba(255,255,255,0.08)',
};

const INPUT_STYLE: React.CSSProperties = {
  width: '100%',
  background: 'var(--color-bg-input)',
  border: '1px solid rgba(255,255,255,0.08)',
  clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
  color: 'var(--color-text-primary)',
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
  background: 'var(--color-brand-orange)',
  color: 'var(--color-text-primary)',
  fontWeight: 600,
  fontSize: '0.9375rem',
  padding: '11px 0',
  width: '100%',
  border: 'none',
  cursor: 'pointer',
  letterSpacing: '0.02em',
};

const STEPS = ['Phone Verified', 'Your Info', 'Patient Link'];

function ProgressStepper({ current }: { current: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0', marginBottom: '32px' }}>
      {STEPS.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', flex: i < STEPS.length - 1 ? 1 : undefined }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
              <div
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  background: done ? 'var(--color-brand-orange)' : active ? 'rgba(255,107,26,0.18)' : 'rgba(255,255,255,0.06)',
                  border: `1px solid ${done ? 'var(--color-brand-orange)' : active ? 'rgba(255,107,26,0.6)' : 'rgba(255,255,255,0.12)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: done ? 'var(--color-text-primary)' : active ? 'var(--color-brand-orange)' : 'rgba(255,255,255,0.3)',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                }}
              >
                {done ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
              <span
                style={{
                  fontSize: '0.6875rem',
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                  color: done ? 'var(--color-brand-orange)' : active ? 'rgba(255,255,255,0.75)' : 'rgba(255,255,255,0.28)',
                  whiteSpace: 'nowrap',
                }}
              >
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                style={{
                  flex: 1,
                  height: '1px',
                  background: done ? 'rgba(255,107,26,0.5)' : 'rgba(255,255,255,0.08)',
                  margin: '0 8px',
                  marginBottom: '20px',
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function RepRegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [relationship, setRelationship] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [patientAccount, setPatientAccount] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const stored = sessionStorage.getItem('rep_phone');
    if (stored) setPhone(stored);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!fullName.trim() || !relationship || !patientAccount.trim()) {
      setError('Full name, relationship, and patient account number are required.');
      return;
    }
    setLoading(true);
    try {
      const token = sessionStorage.getItem('rep_token') ?? '';
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/auth-rep/register`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            full_name: fullName.trim(),
            relationship,
            email: email.trim() || undefined,
            phone: phone.trim() || undefined,
            patient_account_id: patientAccount.trim(),
            delivery_method: 'sms',
          }),
        }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `Registration failed (${res.status})`);
      }
      const body = await res.json();
      if (body.session_id) sessionStorage.setItem('rep_session_id', body.session_id);
      router.push('/portal/rep/sign');
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
      <div style={{ width: '100%', maxWidth: '520px' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <h1 style={{ color: 'var(--color-text-primary)', fontSize: '1.375rem', fontWeight: 700, margin: '0 0 8px' }}>
            Create Your Representative Account
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.875rem', margin: 0 }}>
            Tell us about yourself and the patient you represent
          </p>
        </div>

        <ProgressStepper current={1} />

        {/* Card */}
        <div style={{ ...PANEL_STYLE, padding: '28px 28px 24px' }}>
          <form onSubmit={handleSubmit} noValidate>
            {/* Full Legal Name */}
            <div style={{ marginBottom: '18px' }}>
              <label style={LABEL_STYLE} htmlFor="reg-fullname">Full Legal Name</label>
              <input
                id="reg-fullname"
                type="text"
                autoComplete="name"
                placeholder="As it appears on your government ID"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                style={INPUT_STYLE}
                disabled={loading}
              />
            </div>

            {/* Relationship */}
            <div style={{ marginBottom: '18px' }}>
              <label style={LABEL_STYLE} htmlFor="reg-relationship">Relationship to Patient</label>
              <select
                id="reg-relationship"
                value={relationship}
                onChange={(e) => setRelationship(e.target.value)}
                style={{ ...INPUT_STYLE, appearance: 'none', cursor: 'pointer' }}
                disabled={loading}
              >
                <option value="" disabled>Select relationship...</option>
                <option value="Spouse">Spouse</option>
                <option value="Child">Child</option>
                <option value="Parent">Parent</option>
                <option value="Legal Guardian">Legal Guardian</option>
                <option value="Power of Attorney">Power of Attorney</option>
                <option value="Other">Other</option>
              </select>
            </div>

            {/* Email */}
            <div style={{ marginBottom: '18px' }}>
              <label style={LABEL_STYLE} htmlFor="reg-email">Email Address</label>
              <input
                id="reg-email"
                type="email"
                autoComplete="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={INPUT_STYLE}
                disabled={loading}
              />
            </div>

            {/* Phone (pre-filled) */}
            <div style={{ marginBottom: '18px' }}>
              <label style={LABEL_STYLE} htmlFor="reg-phone">Mobile Number</label>
              <input
                id="reg-phone"
                type="tel"
                autoComplete="tel"
                placeholder="+1 (555) 000-0000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                style={{ ...INPUT_STYLE, color: 'rgba(255,255,255,0.55)' }}
                disabled={loading}
              />
            </div>

            {/* Patient Account Number */}
            <div style={{ marginBottom: '24px' }}>
              <label style={LABEL_STYLE} htmlFor="reg-account">Patient Account Number</label>
              <input
                id="reg-account"
                type="text"
                placeholder="e.g. FMS-00123456"
                value={patientAccount}
                onChange={(e) => setPatientAccount(e.target.value)}
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
              {loading ? 'Saving...' : 'Continue'}
            </button>
          </form>

          <div
            style={{
              marginTop: '16px',
              padding: '10px 12px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.06)',
              clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
            }}
          >
            <p style={{ color: 'rgba(255,255,255,0.35)', fontSize: '0.75rem', margin: 0, lineHeight: 1.5 }}>
              Your information will be verified against patient records within 1 business day
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
