'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';

const PANEL_STYLE = {
  clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
  background: 'var(--color-bg-panel, #0f1720)',
  border: '1px solid rgba(255,255,255,0.08)',
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

const DIGIT_COUNT = 6;
const RESEND_SECONDS = 30;

export default function RepVerifyPage() {
  const router = useRouter();
  const [digits, setDigits] = useState<string[]>(Array(DIGIT_COUNT).fill(''));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [attemptsLeft, setAttemptsLeft] = useState<number | null>(null);
  const [hasError, setHasError] = useState(false);
  const [resendCountdown, setResendCountdown] = useState(RESEND_SECONDS);
  const [resending, setResending] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const otp = digits.join('');
  const allFilled = otp.length === DIGIT_COUNT && digits.every((d) => d !== '');

  // Countdown timer
  useEffect(() => {
    if (resendCountdown <= 0) return;
    const id = setInterval(() => setResendCountdown((c) => c - 1), 1000);
    return () => clearInterval(id);
  }, [resendCountdown]);

  const submit = useCallback(
    async (code: string) => {
      const phone = sessionStorage.getItem('rep_phone') ?? '';
      setLoading(true);
      setError('');
      setHasError(false);
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/auth-rep/verify-otp`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
            session_id: sessionStorage.getItem('rep_session_id') ?? '',
            otp_code: code,
          }),
          }
        );
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          const detail: string = body?.detail ?? `Verification failed (${res.status})`;
          const match = detail.match(/(\d+)\s*attempt/i);
          if (match) setAttemptsLeft(parseInt(match[1], 10));
          setHasError(true);
          setError(
            attemptsLeft !== null
              ? `Incorrect code. ${attemptsLeft} attempts remaining.`
              : detail
          );
          return;
        }
        if (body.token) sessionStorage.setItem('rep_token', body.token);
        if (body.authorized_rep_id) sessionStorage.setItem('rep_id', body.authorized_rep_id);
        const dest = body.is_registered ? '/portal/rep/sign' : '/portal/rep/register';
        router.push(dest);
      } catch (err: unknown) {
        setHasError(true);
        setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
      } finally {
        setLoading(false);
      }
    },
    [router, attemptsLeft]
  );

  function handleDigitChange(index: number, val: string) {
    const char = val.replace(/\D/g, '').slice(-1);
    const next = [...digits];
    next[index] = char;
    setDigits(next);
    setHasError(false);
    setError('');
    if (char && index < DIGIT_COUNT - 1) {
      inputRefs.current[index + 1]?.focus();
    }
    if (char && index === DIGIT_COUNT - 1) {
      const filled = next.every((d) => d !== '');
      if (filled) {
        // auto-submit on a tick so state settles
        setTimeout(() => submit(next.join('')), 0);
      }
    }
  }

  function handleKeyDown(index: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Backspace') {
      if (digits[index]) {
        const next = [...digits];
        next[index] = '';
        setDigits(next);
      } else if (index > 0) {
        inputRefs.current[index - 1]?.focus();
        const next = [...digits];
        next[index - 1] = '';
        setDigits(next);
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < DIGIT_COUNT - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  }

  function handlePaste(e: React.ClipboardEvent) {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, DIGIT_COUNT);
    if (!pasted) return;
    const next = Array(DIGIT_COUNT).fill('');
    pasted.split('').forEach((c, i) => { next[i] = c; });
    setDigits(next);
    const lastIndex = Math.min(pasted.length - 1, DIGIT_COUNT - 1);
    inputRefs.current[lastIndex]?.focus();
    if (pasted.length === DIGIT_COUNT) {
      setTimeout(() => submit(next.join('')), 0);
    }
  }

  async function handleResend() {
    const phone = sessionStorage.getItem('rep_phone') ?? '';
    setResending(true);
    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/auth-rep/register`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
          phone,
          patient_account_id: sessionStorage.getItem('rep_patient_id') ?? '00000000-0000-0000-0000-000000000000',
          relationship: sessionStorage.getItem('rep_relationship') ?? 'self',
          full_name: sessionStorage.getItem('rep_full_name') ?? phone,
          delivery_method: 'sms',
        }),
        }
      );
      setDigits(Array(DIGIT_COUNT).fill(''));
      setError('');
      setHasError(false);
      setResendCountdown(RESEND_SECONDS);
      inputRefs.current[0]?.focus();
    } catch {
      // silent — user can try again
    } finally {
      setResending(false);
    }
  }

  const digitBoxBase: React.CSSProperties = {
    width: '48px',
    height: '56px',
    background: '#0e161f',
    border: `1px solid ${hasError ? 'rgba(220,38,38,0.7)' : 'rgba(255,255,255,0.12)'}`,
    clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
    color: '#fff',
    fontSize: '1.5rem',
    fontWeight: 700,
    textAlign: 'center',
    outline: 'none',
    caretColor: '#ff6b1a',
  };

  return (
    <div
      style={{ background: 'var(--color-bg-base, #0b0f14)', minHeight: '100vh' }}
      className="flex items-center justify-center px-4 py-12"
    >
      <div style={{ width: '100%', maxWidth: '460px' }}>
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
              <rect x="5" y="11" width="14" height="10" rx="1" />
              <path d="M8 11V7a4 4 0 0 1 8 0v4" />
            </svg>
          </div>
          <h1 style={{ color: '#fff', fontSize: '1.375rem', fontWeight: 700, margin: '0 0 8px' }}>
            Enter Verification Code
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.875rem', margin: 0 }}>
            A 6-digit code was sent to your phone
          </p>
        </div>

        {/* Card */}
        <div style={{ ...PANEL_STYLE, padding: '32px 28px 28px' }}>
          {/* Digit boxes */}
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginBottom: '28px' }}>
            {digits.map((digit, i) => (
              <input
                key={i}
                ref={(el) => { inputRefs.current[i] = el; }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleDigitChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                onPaste={handlePaste}
                style={digitBoxBase}
                disabled={loading}
                autoFocus={i === 0}
              />
            ))}
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
                marginBottom: '18px',
                textAlign: 'center',
              }}
            >
              {error}
            </div>
          )}

          <button
            type="button"
            onClick={() => submit(otp)}
            disabled={!allFilled || loading}
            style={{
              ...BTN_PRIMARY,
              opacity: !allFilled || loading ? 0.4 : 1,
              cursor: !allFilled || loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Verifying...' : 'Verify Code'}
          </button>

          {/* Resend */}
          <div style={{ textAlign: 'center', marginTop: '18px' }}>
            {resendCountdown > 0 ? (
              <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8125rem' }}>
                Resend code in {resendCountdown}s
              </span>
            ) : (
              <button
                type="button"
                onClick={handleResend}
                disabled={resending}
                style={{
                  background: 'none',
                  border: 'none',
                  color: resending ? 'rgba(255,255,255,0.3)' : 'rgba(255,107,26,0.8)',
                  fontSize: '0.8125rem',
                  cursor: resending ? 'not-allowed' : 'pointer',
                  padding: 0,
                  textDecoration: 'underline',
                }}
              >
                {resending ? 'Resending...' : 'Resend code'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
