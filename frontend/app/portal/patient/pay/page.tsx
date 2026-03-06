'use client';
import { Suspense } from 'react';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

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

type PatientStatement = {
  id: string;
  data?: {
    incident_date?: string;
    transport_date?: string;
    service_type?: string;
    amount_due_cents?: number;
    amount_paid_cents?: number;
    amount_billed_cents?: number;
  };
};

function PatientPayPageContent() {
  const searchParams = useSearchParams();
  const statementIdFromUrl = searchParams.get('statement_id');
  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || '',
    []
  );

  const [statement, setStatement] = useState<PatientStatement | null>(null);
  const [loadingStatement, setLoadingStatement] = useState(true);
  const [statementError, setStatementError] = useState<string | null>(null);

  const [amount, setAmount] = useState('0.00');
  const [cardNumber, setCardNumber] = useState('');
  const [expiration, setExpiration] = useState('');
  const [cvv, setCvv] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const balanceDue = useMemo(() => {
    const due = statement?.data?.amount_due_cents ?? 0;
    return due / 100;
  }, [statement]);

  const totalBilled = useMemo(() => {
    const billed = statement?.data?.amount_billed_cents;
    if (typeof billed === 'number') return billed / 100;
    const paid = statement?.data?.amount_paid_cents ?? 0;
    const due = statement?.data?.amount_due_cents ?? 0;
    return (paid + due) / 100;
  }, [statement]);

  const insuranceApplied = useMemo(() => {
    return totalBilled - balanceDue;
  }, [totalBilled, balanceDue]);

  useEffect(() => {
    let cancelled = false;

    async function loadStatement() {
      setLoadingStatement(true);
      setStatementError(null);

      try {
        const url = new URL('/api/v1/patient/statements?limit=50', apiBase || window.location.origin);
        const res = await fetch(url.toString(), {
          method: 'GET',
          credentials: 'include',
          headers: {
            Accept: 'application/json',
          },
        });

        if (!res.ok) {
          throw new Error(`Failed to load statements (${res.status})`);
        }

        const payload = await res.json();
        const statements: PatientStatement[] = Array.isArray(payload?.statements)
          ? payload.statements
          : [];

        const picked = statementIdFromUrl
          ? statements.find((s) => s.id === statementIdFromUrl)
          : statements[0];

        if (!picked) {
          throw new Error('No statement found for payment.');
        }

        if (!cancelled) {
          setStatement(picked);
          const due = (picked.data?.amount_due_cents ?? 0) / 100;
          setAmount(due > 0 ? due.toFixed(2) : '0.00');
        }
      } catch (err) {
        if (!cancelled) {
          setStatement(null);
          setStatementError(err instanceof Error ? err.message : 'Unable to load billing data.');
        }
      } finally {
        if (!cancelled) {
          setLoadingStatement(false);
        }
      }
    }

    void loadStatement();
    return () => {
      cancelled = true;
    };
  }, [apiBase, statementIdFromUrl]);

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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);

    if (!statement?.id) {
      setSubmitError('No statement is available for payment.');
      return;
    }

    setSubmitting(true);
    try {
      const url = new URL(`/api/v1/statements/${statement.id}/pay`, apiBase || window.location.origin);
      const res = await fetch(url.toString(), {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });

      if (!res.ok) {
        throw new Error(`Payment initialization failed (${res.status})`);
      }

      const payload = await res.json();
      const checkoutUrl = payload?.checkout_url;
      if (!checkoutUrl || typeof checkoutUrl !== 'string') {
        throw new Error('Checkout URL not returned by backend.');
      }

      window.location.assign(checkoutUrl);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Unable to start payment.');
      setSubmitting(false);
    }
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
          {loadingStatement && (
            <p style={{ marginTop: 8, color: 'var(--color-text-muted)' }}>Loading live statement…</p>
          )}
          {statementError && (
            <p style={{ marginTop: 8, color: '#ef4444' }}>{statementError}</p>
          )}
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
              {
                label: 'Date of Service',
                value:
                  statement?.data?.transport_date ||
                  statement?.data?.incident_date ||
                  '—',
                mono: false,
              },
              { label: 'Service Type', value: statement?.data?.service_type || '—', mono: false },
              { label: 'Total Billed', value: `$${totalBilled.toFixed(2)}`, mono: true },
              {
                label: 'Insurance Applied',
                value: `-$${Math.max(insuranceApplied, 0).toFixed(2)}`,
                mono: true,
                muted: true,
              },
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
                ${balanceDue.toFixed(2)}
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
                  max={Math.max(balanceDue, 1)}
                  required
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  style={{ ...FIELD_STYLE, paddingLeft: 26 }}
                  disabled={loadingStatement || !statement || balanceDue <= 0}
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
                disabled={loadingStatement || !statement || balanceDue <= 0}
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
                  disabled={loadingStatement || !statement || balanceDue <= 0}
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
                  disabled={loadingStatement || !statement || balanceDue <= 0}
                />
              </div>
            </div>

            {submitError && <p style={{ color: '#ef4444', marginTop: -4 }}>{submitError}</p>}

            {/* Submit */}
            <button
              type="submit"
              disabled={submitting || loadingStatement || !statement || balanceDue <= 0}
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
                `Continue to Secure Checkout — $${parseFloat(amount || '0').toFixed(2)}`
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

export default function PatientPayPage() { return <Suspense fallback={<div>Loading...</div>}><PatientPayPageContent /></Suspense>; }
