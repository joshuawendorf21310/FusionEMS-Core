'use client';

import { useState } from 'react';
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
  boxSizing: 'border-box',
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

const BILL = {
  dateOfService: 'January 15, 2026',
  serviceType: 'Emergency Transport — ALS Level 1',
  totalBilled: 385.0,
  insuranceApplied: -210.0,
  balanceDue: 175.0,
};

export default function PatientPayPage() {
  const [amount, setAmount] = useState(BILL.balanceDue.toFixed(2));
  const [cardNumber, setCardNumber] = useState('');
  const [expiration, setExpiration] = useState('');
  const [cvv, setCvv] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function formatCard(val: string) {
    return val
      .replace(/\D/g, '')
      .slice(0, 16)
      .replace(/(.{4})/g, '$1 ')
      .trim();
  }

  function formatExp(val: string) {
    return val
      .replace(/\D/g, '')
      .slice(0, 4)
      .replace(/^(\d{2})(\d)/, '$1/$2');
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setTimeout(() => {
      window.location.href = '/portal/patient/receipt';
    }, 1600);
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--color-bg-base)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: '40px 16px',
      }}
    >
      <div style={{ width: '100%', maxWidth: 520 }}>
        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <div
            style={{
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-micro)',
              fontWeight: 600,
              letterSpacing: 'var(--tracking-micro)',
              textTransform: 'uppercase',
              color: 'var(--color-brand-orange)',
              marginBottom: 6,
            }}
          >
            Patient Portal
          </div>
          <h1
            style={{
              fontSize: 'var(--text-h2)',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              lineHeight: 'var(--leading-tight)',
            }}
          >
            Make a Payment
          </h1>
        </div>

        {/* Bill Summary */}
        <div
          style={{
            background: 'var(--color-bg-panel)',
            border: '1px solid var(--color-border-default)',
            borderLeft: '3px solid var(--color-system-billing)',
            clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
            marginBottom: 16,
          }}
        >
          <div
            className="hud-rail"
            style={{
              padding: '10px 16px',
              borderBottom: '1px solid var(--color-border-default)',
            }}
          >
            <span
              style={{
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-label)',
                fontWeight: 600,
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
                color: 'var(--color-text-muted)',
              }}
            >
              Bill Summary
            </span>
          </div>
          <div style={{ padding: '0 16px 4px' }}>
            {[
              { label: 'Date of Service', value: BILL.dateOfService, mono: false },
              { label: 'Service Type', value: BILL.serviceType, mono: false },
              { label: 'Total Billed', value: `$${BILL.totalBilled.toFixed(2)}`, mono: true },
              { label: 'Insurance Applied', value: `-$${Math.abs(BILL.insuranceApplied).toFixed(2)}`, mono: true, muted: true },
            ].map((row) => (
              <div
                key={row.label}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 0',
                  borderBottom: '1px solid var(--color-border-subtle)',
                }}
              >
                <span
                  style={{
                    fontFamily: 'var(--font-label)',
                    fontSize: 'var(--text-label)',
                    fontWeight: 600,
                    letterSpacing: 'var(--tracking-label)',
                    textTransform: 'uppercase',
                    color: 'var(--color-text-muted)',
                  }}
                >
                  {row.label}
                </span>
                <span
                  style={{
                    fontSize: 'var(--text-body)',
                    fontFamily: row.mono ? 'var(--font-mono)' : 'var(--font-sans)',
                    color: row.muted ? 'var(--color-status-active)' : 'var(--color-text-secondary)',
                  }}
                >
                  {row.value}
                </span>
              </div>
            ))}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px 0',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--font-label)',
                  fontSize: 'var(--text-label)',
                  fontWeight: 700,
                  letterSpacing: 'var(--tracking-label)',
                  textTransform: 'uppercase',
                  color: 'var(--color-text-primary)',
                }}
              >
                Balance Due
              </span>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--text-h3)',
                  fontWeight: 700,
                  color: 'var(--color-brand-orange)',
                }}
              >
                ${BILL.balanceDue.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Payment Form */}
        <div
          style={{
            background: 'var(--color-bg-panel)',
            border: '1px solid var(--color-border-default)',
            clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
            padding: 24,
          }}
        >
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {/* Payment amount */}
            <div>
              <label style={LABEL_STYLE} htmlFor="amount">Payment Amount</label>
              <div style={{ position: 'relative' }}>
                <span
                  style={{
                    position: 'absolute',
                    left: 12,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--color-text-muted)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 'var(--text-body)',
                    pointerEvents: 'none',
                  }}
                >
                  $
                </span>
                <input
                  id="amount"
                  type="number"
                  step="0.01"
                  min="1"
                  max={BILL.balanceDue}
                  required
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  style={{ ...FIELD_STYLE, paddingLeft: 26 }}
                />
              </div>
            </div>

            {/* Card number */}
            <div>
              <label style={LABEL_STYLE} htmlFor="cardNumber">Card Number</label>
              <input
                id="cardNumber"
                type="text"
                inputMode="numeric"
                autoComplete="cc-number"
                required
                maxLength={19}
                value={cardNumber}
                onChange={(e) => setCardNumber(formatCard(e.target.value))}
                style={FIELD_STYLE}
                placeholder="1234 5678 9012 3456"
              />
            </div>

            {/* Exp + CVV */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div>
                <label style={LABEL_STYLE} htmlFor="expiration">Expiration</label>
                <input
                  id="expiration"
                  type="text"
                  inputMode="numeric"
                  autoComplete="cc-exp"
                  required
                  maxLength={5}
                  value={expiration}
                  onChange={(e) => setExpiration(formatExp(e.target.value))}
                  style={FIELD_STYLE}
                  placeholder="MM/YY"
                />
              </div>
              <div>
                <label style={LABEL_STYLE} htmlFor="cvv">CVV</label>
                <input
                  id="cvv"
                  type="password"
                  inputMode="numeric"
                  autoComplete="cc-csc"
                  required
                  maxLength={4}
                  value={cvv}
                  onChange={(e) => setCvv(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  style={FIELD_STYLE}
                  placeholder="•••"
                />
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={submitting}
              style={{
                marginTop: 4,
                background: submitting ? 'var(--color-brand-orange-dim)' : 'var(--color-brand-orange)',
                color: '#000',
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-label)',
                fontWeight: 700,
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
                border: 'none',
                padding: '13px 20px',
                cursor: submitting ? 'not-allowed' : 'pointer',
                clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              {submitting ? (
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
                  Processing...
                </>
              ) : (
                `Pay Securely — $${parseFloat(amount || '0').toFixed(2)}`
              )}
            </button>
          </form>
        </div>

        {/* Security badge */}
        <div
          style={{
            marginTop: 14,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
          }}
        >
          <span style={{ fontSize: 14, color: 'var(--color-status-active)' }}>🔒</span>
          <span
            style={{
              fontSize: 11,
              color: 'var(--color-text-muted)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            256-bit SSL encrypted · Powered by Stripe
          </span>
        </div>

        {/* PCI notice */}
        <p
          style={{
            textAlign: 'center',
            fontSize: 10,
            color: 'var(--color-text-muted)',
            marginTop: 8,
            fontFamily: 'var(--font-label)',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}
        >
          PCI DSS Level 1 Compliant · Card data is never stored on our servers
        </p>

        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Link
            href="/portal/patient/statements"
            style={{
              fontSize: 'var(--text-body)',
              color: 'var(--color-text-muted)',
              textDecoration: 'none',
            }}
          >
            ← Back to Statements
          </Link>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        input:focus { border-color: var(--color-border-focus) !important; }
        input[type=number]::-webkit-inner-spin-button,
        input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; }
      `}</style>
    </div>
  );
}
