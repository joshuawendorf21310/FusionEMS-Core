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

interface InsuranceFields {
  carrier: string;
  policyNumber: string;
  groupNumber: string;
  subscriberName: string;
}

const EMPTY_INSURANCE: InsuranceFields = {
  carrier: '',
  policyNumber: '',
  groupNumber: '',
  subscriberName: '',
};

function InsuranceSection({
  title,
  accent,
  data,
  onChange,
  hasSecondary,
  onAdd,
}: {
  title: string;
  accent: string;
  data: InsuranceFields | null;
  onChange?: (field: keyof InsuranceFields, value: string) => void;
  hasSecondary?: boolean;
  onAdd?: () => void;
}) {
  const isEmptySecondary = data === null;

  return (
    <div
      style={{
        background: 'var(--color-bg-panel)',
        border: '1px solid var(--color-border-default)',
        borderLeft: `3px solid ${accent}`,
        clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
        marginBottom: 16,
      }}
    >
      <div
        className="hud-rail"
        style={{
          padding: '10px 16px',
          borderBottom: '1px solid var(--color-border-default)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-label)',
            fontSize: 'var(--text-label)',
            fontWeight: 600,
            letterSpacing: 'var(--tracking-label)',
            textTransform: 'uppercase',
            color: 'var(--color-text-secondary)',
          }}
        >
          {title}
        </span>
      </div>

      <div style={{ padding: 20 }}>
        {isEmptySecondary ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 12,
              padding: '20px 0',
            }}
          >
            <p
              style={{
                fontSize: 'var(--text-body)',
                color: 'var(--color-text-muted)',
                textAlign: 'center',
              }}
            >
              No secondary insurance on file.
            </p>
            <button
              onClick={onAdd}
              style={{
                background: 'var(--color-brand-orange-ghost)',
                border: '1px solid var(--color-brand-orange)',
                color: 'var(--color-brand-orange)',
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-label)',
                fontWeight: 700,
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
                padding: '9px 20px',
                cursor: 'pointer',
                clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
              }}
            >
              + Add Secondary Insurance
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div>
                <label style={LABEL_STYLE}>Carrier</label>
                <input
                  type="text"
                  value={data.carrier}
                  onChange={(e) => onChange?.('carrier', e.target.value)}
                  style={FIELD_STYLE}
                  placeholder="Blue Cross Blue Shield"
                />
              </div>
              <div>
                <label style={LABEL_STYLE}>Subscriber Name</label>
                <input
                  type="text"
                  value={data.subscriberName}
                  onChange={(e) => onChange?.('subscriberName', e.target.value)}
                  style={FIELD_STYLE}
                  placeholder="Jane M. Doe"
                />
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div>
                <label style={LABEL_STYLE}>Policy #</label>
                <input
                  type="text"
                  value={data.policyNumber}
                  onChange={(e) => onChange?.('policyNumber', e.target.value)}
                  style={FIELD_STYLE}
                  placeholder="XYZ-123456789"
                />
              </div>
              <div>
                <label style={LABEL_STYLE}>Group #</label>
                <input
                  type="text"
                  value={data.groupNumber}
                  onChange={(e) => onChange?.('groupNumber', e.target.value)}
                  style={FIELD_STYLE}
                  placeholder="GRP-78901"
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PatientInsurancePage() {
  const [primary, setPrimary] = useState<InsuranceFields>({
    carrier: 'Blue Cross Blue Shield',
    policyNumber: 'BCBS-4829017',
    groupNumber: 'GRP-1045',
    subscriberName: 'Jane M. Doe',
  });
  const [secondary, setSecondary] = useState<InsuranceFields | null>(null);
  const [saved, setSaved] = useState(false);

  function handlePrimaryChange(field: keyof InsuranceFields, value: string) {
    setPrimary((prev) => ({ ...prev, [field]: value }));
    setSaved(false);
  }

  function handleSecondaryChange(field: keyof InsuranceFields, value: string) {
    setSecondary((prev) => (prev ? { ...prev, [field]: value } : prev));
    setSaved(false);
  }

  function handleSave() {
    setSaved(true);
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
      <div style={{ width: '100%', maxWidth: 560 }}>
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
            Insurance Information
          </h1>
        </div>

        <InsuranceSection
          title="Primary Insurance"
          accent="var(--color-brand-orange)"
          data={primary}
          onChange={handlePrimaryChange}
        />

        <InsuranceSection
          title="Secondary Insurance"
          accent="var(--color-system-billing)"
          data={secondary}
          onChange={handleSecondaryChange}
          onAdd={() => setSecondary({ ...EMPTY_INSURANCE })}
        />

        {/* Update button */}
        <button
          onClick={handleSave}
          style={{
            background: 'var(--color-brand-orange)',
            color: '#000',
            fontFamily: 'var(--font-label)',
            fontSize: 'var(--text-label)',
            fontWeight: 700,
            letterSpacing: 'var(--tracking-label)',
            textTransform: 'uppercase',
            border: 'none',
            padding: '13px 28px',
            cursor: 'pointer',
            clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
            width: '100%',
          }}
        >
          Update Insurance
        </button>

        {/* Confirmation */}
        {saved && (
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
              Insurance information saved successfully.
            </span>
          </div>
        )}

        {/* Review notice */}
        <div
          style={{
            marginTop: 14,
            padding: '12px 16px',
            background: 'rgba(255, 107, 26, 0.05)',
            border: '1px solid rgba(255, 107, 26, 0.15)',
            clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)',
          }}
        >
          <p
            style={{
              fontSize: 11,
              color: 'var(--color-text-muted)',
              lineHeight: 'var(--leading-base)',
            }}
          >
            Changes are reviewed by billing staff within 1 business day. You will receive a confirmation once your insurance update has been processed.
          </p>
        </div>

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

      <style>{`
        input:focus { border-color: var(--color-border-focus) !important; }
      `}</style>
    </div>
  );
}
