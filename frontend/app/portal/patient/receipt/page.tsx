'use client';

import Link from 'next/link';

const RECEIPT = {
  confirmation: 'FQ-2026-0127-8834',
  date: 'February 27, 2026',
  amount: '$175.00',
  last4: '4242',
  status: 'PAID',
};

export default function PatientReceiptPage() {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--color-bg-base)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: '60px 16px 40px',
      }}
    >
      <div style={{ width: '100%', maxWidth: 480 }}>
        {/* Success indicator */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            marginBottom: 32,
          }}
        >
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: 'rgba(76, 175, 80, 0.12)',
              border: '2px solid var(--color-status-active)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 32,
              color: 'var(--color-status-active)',
              fontWeight: 700,
              marginBottom: 20,
            }}
          >
            ✓
          </div>
          <h1
            style={{
              fontSize: 'var(--text-h2)',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              lineHeight: 'var(--leading-tight)',
              textAlign: 'center',
              marginBottom: 6,
            }}
          >
            Payment Received
          </h1>
          <p
            style={{
              fontSize: 'var(--text-body)',
              color: 'var(--color-text-muted)',
              textAlign: 'center',
            }}
          >
            Your payment has been processed successfully.
          </p>
        </div>

        {/* Receipt card */}
        <div
          style={{
            background: 'var(--color-bg-panel)',
            border: '1px solid var(--color-border-default)',
            borderLeft: '3px solid var(--color-status-active)',
            clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
            marginBottom: 20,
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
              Receipt Details
            </span>
          </div>
          <div style={{ padding: '0 16px 4px' }}>
            {[
              { label: 'Confirmation #', value: RECEIPT.confirmation, mono: true },
              { label: 'Date', value: RECEIPT.date, mono: false },
              { label: 'Amount', value: RECEIPT.amount, mono: true, highlight: true },
              { label: 'Card', value: `•••• •••• •••• ${RECEIPT.last4}`, mono: true },
            ].map((row) => (
              <div
                key={row.label}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '11px 0',
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
                    fontSize: row.highlight ? 'var(--text-body-lg)' : 'var(--text-body)',
                    fontFamily: row.mono ? 'var(--font-mono)' : 'var(--font-sans)',
                    fontWeight: row.highlight ? 700 : 400,
                    color: row.highlight
                      ? 'var(--color-text-primary)'
                      : 'var(--color-text-secondary)',
                  }}
                >
                  {row.value}
                </span>
              </div>
            ))}
            {/* Status row */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '11px 0',
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
                Status
              </span>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  background: 'rgba(76, 175, 80, 0.12)',
                  border: '1px solid rgba(76, 175, 80, 0.35)',
                  clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
                  padding: '3px 10px',
                  fontFamily: 'var(--font-label)',
                  fontSize: 'var(--text-micro)',
                  fontWeight: 700,
                  letterSpacing: 'var(--tracking-micro)',
                  textTransform: 'uppercase',
                  color: 'var(--color-status-active)',
                }}
              >
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: 'var(--color-status-active)',
                    flexShrink: 0,
                  }}
                />
                {RECEIPT.status}
              </span>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <button
            onClick={() => window.print()}
            style={{
              background: 'var(--color-bg-panel)',
              border: '1px solid var(--color-border-strong)',
              color: 'var(--color-text-primary)',
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-label)',
              fontWeight: 600,
              letterSpacing: 'var(--tracking-label)',
              textTransform: 'uppercase',
              padding: '12px 20px',
              cursor: 'pointer',
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
              width: '100%',
            }}
          >
            Download Receipt (PDF)
          </button>

          <Link
            href="/portal/patient/statements"
            style={{
              display: 'block',
              background: 'var(--color-brand-orange)',
              color: '#000',
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-label)',
              fontWeight: 700,
              letterSpacing: 'var(--tracking-label)',
              textTransform: 'uppercase',
              padding: '12px 20px',
              cursor: 'pointer',
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
              width: '100%',
              textAlign: 'center',
              textDecoration: 'none',
              boxSizing: 'border-box',
            }}
          >
            Return to Account
          </Link>
        </div>

        {/* Email receipt link */}
        <div style={{ textAlign: 'center', marginTop: 18 }}>
          <button
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 'var(--text-body)',
              color: 'var(--color-text-muted)',
              textDecoration: 'underline',
              textDecorationColor: 'rgba(255,255,255,0.15)',
            }}
            onClick={() => alert('Receipt emailed to your address on file.')}
          >
            Email receipt
          </button>
        </div>
      </div>
    </div>
  );
}
