'use client';

import { useState } from 'react';
import Link from 'next/link';

const TOTAL_BALANCE = 520.0;

const PLANS = [
  { id: '3mo', months: 3, monthly: 173.33 },
  { id: '6mo', months: 6, monthly: 86.67 },
  { id: '12mo', months: 12, monthly: 43.33 },
];

export default function PatientPlanPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [enrolled, setEnrolled] = useState(false);
  const [autopay, setAutopay] = useState(false);

  function handleEnroll() {
    if (!selected) return;
    setEnrolled(true);
  }

  const selectedPlan = PLANS.find((p) => p.id === selected);

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
            Payment Plan
          </h1>
        </div>

        {/* Balance summary */}
        <div
          style={{
            background: 'var(--color-bg-panel)',
            border: '1px solid var(--color-border-default)',
            borderLeft: '3px solid var(--color-brand-orange)',
            clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
            padding: '16px 20px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div
              style={{
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-label)',
                fontWeight: 600,
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
                color: 'var(--color-text-muted)',
                marginBottom: 4,
              }}
            >
              Total Balance
            </div>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 'var(--text-h1)',
                fontWeight: 700,
                color: 'var(--color-brand-orange)',
              }}
            >
              ${TOTAL_BALANCE.toFixed(2)}
            </div>
          </div>
          <div
            style={{
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-micro)',
              fontWeight: 600,
              letterSpacing: 'var(--tracking-micro)',
              textTransform: 'uppercase',
              color: 'var(--color-text-muted)',
              textAlign: 'right',
            }}
          >
            EMS Services<br />
            <span style={{ color: 'var(--color-text-secondary)' }}>2026 YTD</span>
          </div>
        </div>

        {/* Plan options */}
        <div
          style={{
            fontFamily: 'var(--font-label)',
            fontSize: 'var(--text-label)',
            fontWeight: 600,
            letterSpacing: 'var(--tracking-label)',
            textTransform: 'uppercase',
            color: 'var(--color-text-muted)',
            marginBottom: 12,
          }}
        >
          Select a Plan
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
          {PLANS.map((plan) => {
            const isSelected = selected === plan.id;
            return (
              <button
                key={plan.id}
                onClick={() => setSelected(plan.id)}
                style={{
                  background: isSelected
                    ? 'rgba(255, 107, 26, 0.08)'
                    : 'var(--color-bg-panel)',
                  border: isSelected
                    ? '1px solid var(--color-brand-orange)'
                    : '1px solid var(--color-border-default)',
                  borderLeft: isSelected
                    ? '3px solid var(--color-brand-orange)'
                    : '3px solid transparent',
                  clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
                  padding: '16px 20px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  textAlign: 'left',
                  transition: 'border-color 0.15s, background 0.15s',
                  width: '100%',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  {/* Radio dot */}
                  <div
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: '50%',
                      border: `2px solid ${isSelected ? 'var(--color-brand-orange)' : 'var(--color-border-strong)'}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {isSelected && (
                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: 'var(--color-brand-orange)',
                        }}
                      />
                    )}
                  </div>
                  <div>
                    <div
                      style={{
                        fontFamily: 'var(--font-label)',
                        fontSize: 'var(--text-label)',
                        fontWeight: 700,
                        letterSpacing: 'var(--tracking-label)',
                        textTransform: 'uppercase',
                        color: isSelected ? 'var(--color-brand-orange)' : 'var(--color-text-primary)',
                      }}
                    >
                      {plan.months} Months
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: 'var(--color-text-muted)',
                        marginTop: 2,
                      }}
                    >
                      {plan.months} equal payments
                    </div>
                  </div>
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 'var(--text-h3)',
                    fontWeight: 700,
                    color: isSelected ? 'var(--color-brand-orange)' : 'var(--color-text-secondary)',
                  }}
                >
                  ${plan.monthly.toFixed(2)}
                  <span
                    style={{
                      fontFamily: 'var(--font-label)',
                      fontSize: 10,
                      fontWeight: 500,
                      color: 'var(--color-text-muted)',
                      letterSpacing: '0.05em',
                      marginLeft: 4,
                    }}
                  >
                    /mo
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {/* AutoPay option */}
        <div
          style={{
            background: 'var(--color-bg-panel)',
            border: '1px solid var(--color-border-default)',
            clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
            padding: '14px 18px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
          }}
        >
          <div>
            <div
              style={{
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-label)',
                fontWeight: 600,
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
                color: 'var(--color-text-secondary)',
                marginBottom: 3,
              }}
            >
              Enable AutoPay
            </div>
            <p style={{ fontSize: 11, color: 'var(--color-text-muted)', lineHeight: 1.4 }}>
              Automatically charge your card on the same day each month. Cancel anytime.
            </p>
          </div>
          <button
            onClick={() => setAutopay((v) => !v)}
            style={{
              width: 44,
              height: 24,
              borderRadius: 12,
              background: autopay ? 'var(--color-brand-orange)' : 'var(--color-bg-overlay)',
              border: `1px solid ${autopay ? 'var(--color-brand-orange)' : 'var(--color-border-strong)'}`,
              cursor: 'pointer',
              position: 'relative',
              flexShrink: 0,
              transition: 'background 0.15s, border-color 0.15s',
              padding: 0,
            }}
            aria-checked={autopay}
            role="switch"
          >
            <span
              style={{
                position: 'absolute',
                top: 2,
                left: autopay ? 22 : 2,
                width: 18,
                height: 18,
                borderRadius: '50%',
                background: 'var(--color-text-primary)',
                transition: 'left 0.15s',
              }}
            />
          </button>
        </div>

        {/* Enroll button */}
        <button
          onClick={handleEnroll}
          disabled={!selected || enrolled}
          style={{
            background:
              !selected || enrolled
                ? 'var(--color-brand-orange-dim)'
                : 'var(--color-brand-orange)',
            color: '#000',
            fontFamily: 'var(--font-label)',
            fontSize: 'var(--text-label)',
            fontWeight: 700,
            letterSpacing: 'var(--tracking-label)',
            textTransform: 'uppercase',
            border: 'none',
            padding: '13px 28px',
            cursor: !selected || enrolled ? 'not-allowed' : 'pointer',
            clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
            width: '100%',
          }}
        >
          {enrolled
            ? `Enrolled — ${selectedPlan?.months} Month Plan`
            : selected
            ? `Enroll in ${selectedPlan?.months}-Month Plan — $${selectedPlan?.monthly.toFixed(2)}/mo`
            : 'Select a Plan to Enroll'}
        </button>

        {enrolled && (
          <div
            style={{
              marginTop: 12,
              padding: '10px 16px',
              background: 'rgba(76, 175, 80, 0.08)',
              border: '1px solid rgba(76, 175, 80, 0.3)',
              clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <span style={{ color: 'var(--color-status-active)', fontSize: 14 }}>✓</span>
            <span style={{ fontSize: 'var(--text-body)', color: 'var(--color-status-active)' }}>
              You have been enrolled in the {selectedPlan?.months}-month payment plan.
              {autopay && ' AutoPay is enabled.'}
            </span>
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: 20 }}>
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
    </div>
  );
}
