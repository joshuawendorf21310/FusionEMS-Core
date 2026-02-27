'use client';

import React, { useState } from 'react';
import AppShell from '@/components/AppShell';
import { MetricPlate, PlateCard } from '@/components/ui/PlateCard';
import { StatusChip } from '@/components/ui/StatusChip';

// ─── Types ───────────────────────────────────────────────────────────────────

type ChipStatus = 'active' | 'warning' | 'critical' | 'info' | 'neutral';

interface ComplianceItem {
  name:         string;
  description:  string;
  status:       ChipStatus;
  statusLabel:  string;
  lastChecked:  string;
}

type TabKey = 'nemsis' | 'hipaa' | 'pcr' | 'billing' | 'accreditation';

// ─── Static compliance data ───────────────────────────────────────────────────
const STATIC_DATA: Record<TabKey, ComplianceItem[]> = {
  nemsis: [
    {
      name:        'Schema Validation',
      description: 'NEMSIS v3.5.1 XSD schema conformance check against all submitted records',
      status:      'active',
      statusLabel: 'Passing',
      lastChecked: '2026-02-27 06:00',
    },
    {
      name:        'Required Fields',
      description: 'Mandatory NEMSIS data elements present in 100% of active PCRs',
      status:      'active',
      statusLabel: 'Passing',
      lastChecked: '2026-02-27 06:00',
    },
    {
      name:        'Demographic Completeness',
      description: 'Patient demographic fields fully populated per state requirement',
      status:      'warning',
      statusLabel: '94.1% Complete',
      lastChecked: '2026-02-27 04:30',
    },
    {
      name:        'Timestamp Accuracy',
      description: 'Dispatch, on-scene, and transport times cross-validated against CAD feed',
      status:      'active',
      statusLabel: 'Passing',
      lastChecked: '2026-02-27 05:45',
    },
    {
      name:        'Unit Certification',
      description: 'All responding units certified at appropriate ALS/BLS level per call type',
      status:      'active',
      statusLabel: 'Compliant',
      lastChecked: '2026-02-26 23:00',
    },
    {
      name:        'Crew Credentials',
      description: 'Active state certifications verified for all personnel on submitted runs',
      status:      'warning',
      statusLabel: '2 Expiring Soon',
      lastChecked: '2026-02-27 00:00',
    },
    {
      name:        'Dispatch Codes',
      description: 'EMD nature codes mapped to valid NEMSIS situation codes in all records',
      status:      'active',
      statusLabel: 'Passing',
      lastChecked: '2026-02-27 06:00',
    },
    {
      name:        'Protocol Adherence',
      description: 'Medication and procedure documentation matches active protocol set',
      status:      'active',
      statusLabel: 'Passing',
      lastChecked: '2026-02-26 22:00',
    },
  ],

  hipaa: [
    {
      name:        'PHI Encryption at Rest',
      description: 'All PHI stored in database encrypted via AES-256; keys managed in AWS KMS',
      status:      'active',
      statusLabel: 'Enforced',
      lastChecked: '2026-02-27 06:00',
    },
    {
      name:        'PHI Encryption in Transit',
      description: 'TLS 1.3 enforced on all API endpoints and inter-service communication',
      status:      'active',
      statusLabel: 'Enforced',
      lastChecked: '2026-02-27 06:00',
    },
    {
      name:        'Access Log Audit',
      description: 'All PHI access events logged to immutable CloudWatch Logs with 7-year retention',
      status:      'active',
      statusLabel: 'Active',
      lastChecked: '2026-02-27 06:00',
    },
    {
      name:        'Minimum Necessary Rule',
      description: 'Role-based access controls limit PHI exposure to job-function scope only',
      status:      'active',
      statusLabel: 'Enforced',
      lastChecked: '2026-02-27 04:00',
    },
    {
      name:        'BAA Status',
      description: 'Executed Business Associate Agreements on file for all covered sub-processors',
      status:      'warning',
      statusLabel: '1 Pending Renewal',
      lastChecked: '2026-02-26 17:00',
    },
    {
      name:        'Breach Notification Procedure',
      description: 'Incident response runbook reviewed and contact list current',
      status:      'active',
      statusLabel: 'Current',
      lastChecked: '2026-01-15 09:00',
    },
    {
      name:        'Workforce Training',
      description: 'Annual HIPAA training completion rate for all credentialed staff',
      status:      'warning',
      statusLabel: '87% Complete',
      lastChecked: '2026-02-20 00:00',
    },
    {
      name:        'Data Retention',
      description: 'PCR records retained per CMS 7-year rule; automated lifecycle policies active',
      status:      'active',
      statusLabel: 'Compliant',
      lastChecked: '2026-02-01 00:00',
    },
  ],

  pcr: [
    {
      name:        'Avg Completion Time',
      description: 'Mean time from call close to PCR finalization across all active units',
      status:      'warning',
      statusLabel: '38 min avg',
      lastChecked: '2026-02-27 06:00',
    },
    {
      name:        'Fields Missing',
      description: 'PCRs with one or more required billing or clinical fields left blank',
      status:      'critical',
      statusLabel: '14 Records',
      lastChecked: '2026-02-27 06:00',
    },
    {
      name:        'Late Signatures',
      description: 'Crew chief signatures not applied within the required 24-hour window',
      status:      'warning',
      statusLabel: '6 Pending',
      lastChecked: '2026-02-27 05:00',
    },
    {
      name:        'Protocol Deviations',
      description: 'Documented deviations from standing orders requiring medical director review',
      status:      'info',
      statusLabel: '2 Open',
      lastChecked: '2026-02-26 20:00',
    },
    {
      name:        'Supervisor Reviews',
      description: 'QA supervisor review queue — records flagged for clinical documentation issues',
      status:      'warning',
      statusLabel: '9 Queued',
      lastChecked: '2026-02-27 06:00',
    },
  ],

  billing: [
    {
      name:        'ABN Compliance',
      description: 'Advance Beneficiary Notice obtained and documented for all non-covered transports',
      status:      'active',
      statusLabel: 'Compliant',
      lastChecked: '2026-02-27 06:00',
    },
    {
      name:        'Medical Necessity Docs',
      description: 'Certificate of Medical Necessity on file for all recurring transport authorizations',
      status:      'warning',
      statusLabel: '3 Missing',
      lastChecked: '2026-02-27 05:00',
    },
    {
      name:        'Modifier Accuracy',
      description: 'ALS/BLS level modifiers validated against PCR clinical narrative and crew cert level',
      status:      'active',
      statusLabel: '99.1% Accurate',
      lastChecked: '2026-02-27 06:00',
    },
    {
      name:        'Diagnosis Coding',
      description: 'ICD-10 diagnosis codes present and valid on all submitted professional claims',
      status:      'active',
      statusLabel: 'Passing',
      lastChecked: '2026-02-27 06:00',
    },
    {
      name:        'Prior Auth Rate',
      description: 'Percentage of non-emergency transports with payer prior authorization on file',
      status:      'warning',
      statusLabel: '91% Coverage',
      lastChecked: '2026-02-26 22:00',
    },
    {
      name:        'PTAN Active',
      description: 'Medicare Provider Transaction Access Number current and billing privileges active',
      status:      'active',
      statusLabel: 'Active',
      lastChecked: '2026-02-01 00:00',
    },
  ],

  accreditation: [
    {
      name:        'CoAEMSP Status',
      description: 'Committee on Accreditation of EMS Professions program accreditation standing',
      status:      'active',
      statusLabel: 'Accredited',
      lastChecked: '2026-01-01 00:00',
    },
    {
      name:        'CAAS Status',
      description: 'Commission on Accreditation of Ambulance Services certification current',
      status:      'info',
      statusLabel: 'Under Review',
      lastChecked: '2026-02-14 00:00',
    },
    {
      name:        'State Licensure',
      description: 'State EMS agency operating license current and all endorsements valid',
      status:      'active',
      statusLabel: 'Current',
      lastChecked: '2026-02-01 00:00',
    },
    {
      name:        'Equipment Calibration',
      description: 'Cardiac monitors, ventilators, and stretchers on current calibration schedule',
      status:      'warning',
      statusLabel: '4 Units Due',
      lastChecked: '2026-02-25 08:00',
    },
    {
      name:        'QA Meeting Cadence',
      description: 'Monthly quality assurance committee meetings documented and minutes filed',
      status:      'active',
      statusLabel: 'On Schedule',
      lastChecked: '2026-02-03 00:00',
    },
    {
      name:        'CE Compliance Rate',
      description: 'Continuing education hours on track for all certified personnel this cycle',
      status:      'warning',
      statusLabel: '83% On Track',
      lastChecked: '2026-02-27 00:00',
    },
  ],
};

// ─── Tab configuration ────────────────────────────────────────────────────────

const TABS: { key: TabKey; label: string }[] = [
  { key: 'nemsis',        label: 'NEMSIS'             },
  { key: 'hipaa',         label: 'HIPAA'              },
  { key: 'pcr',           label: 'PCR Completion'     },
  { key: 'billing',       label: 'Billing Compliance' },
  { key: 'accreditation', label: 'Accreditation'      },
];

// ─── Stat cards ───────────────────────────────────────────────────────────────

const STAT_CARDS = {
  overallScore:   { label: 'Overall Score',     value: '94.2%', accent: 'compliance' },
  openViolations: { label: 'Open Violations',   value: '7',     accent: 'warning'   },
  pendingReviews: { label: 'Pending Reviews',   value: '18',    accent: 'cad'       },
  lastAuditDate:  { label: 'Last Audit Date',   value: 'Feb 14', accent: 'billing'  },
};

// ─── Compliance item row ──────────────────────────────────────────────────────

function ComplianceRow({ item }: { item: ComplianceItem }) {
  return (
    <div
      className="flex items-start justify-between gap-4 px-4 py-3"
      style={{ borderBottom: '1px solid var(--color-border-subtle)' }}
    >
      <div className="min-w-0 flex-1">
        <p
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize:   'var(--text-body)',
            color:      'var(--color-text-primary)',
            lineHeight: 'var(--leading-snug)',
          }}
        >
          {item.name}
        </p>
        <p
          className="micro-caps mt-0.5"
          style={{ color: 'var(--color-text-muted)' }}
        >
          {item.description}
        </p>
      </div>

      <div className="flex shrink-0 flex-col items-end gap-1.5">
        <StatusChip status={item.status} size="sm">
          {item.statusLabel}
        </StatusChip>
        <span
          className="micro-caps"
          style={{ color: 'var(--color-text-muted)' }}
        >
          {item.lastChecked}
        </span>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CompliancePage() {
  const [activeTab, setActiveTab] = useState<TabKey>('nemsis');

  const items = STATIC_DATA[activeTab];

  return (
    <AppShell>
      {/* ── Page header ────────────────────────────────────────────────── */}
      <div
        className="hud-rail mb-6 pb-4"
        style={{ borderBottom: '1px solid var(--color-border-default)' }}
      >
        <h1
          className="label-caps"
          style={{
            fontSize: 'var(--text-h2)',
            color:    'var(--color-text-primary)',
          }}
        >
          Compliance Monitor
        </h1>
        <p
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize:   'var(--text-body)',
            color:      'var(--color-text-secondary)',
            marginTop:  4,
          }}
        >
          Real-time regulatory adherence across all active systems
        </p>
      </div>

      {/* ── Stat cards ─────────────────────────────────────────────────── */}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricPlate
          label={STAT_CARDS.overallScore.label}
          value={STAT_CARDS.overallScore.value}
          accent={STAT_CARDS.overallScore.accent}
          trendDirection="up"
          trendPositive
          trend="+0.8 pts this week"
        />
        <MetricPlate
          label={STAT_CARDS.openViolations.label}
          value={STAT_CARDS.openViolations.value}
          accent={STAT_CARDS.openViolations.accent}
          trendDirection="down"
          trendPositive
          trend="-3 since last cycle"
        />
        <MetricPlate
          label={STAT_CARDS.pendingReviews.label}
          value={STAT_CARDS.pendingReviews.value}
          accent={STAT_CARDS.pendingReviews.accent}
        />
        <MetricPlate
          label={STAT_CARDS.lastAuditDate.label}
          value={STAT_CARDS.lastAuditDate.value}
          accent={STAT_CARDS.lastAuditDate.accent}
          trend="Internal QA"
          trendDirection="neutral"
        />
      </div>

      {/* ── Tab bar ────────────────────────────────────────────────────── */}
      <div
        className="chamfer-4 mb-4 flex p-0.5"
        style={{
          backgroundColor: 'var(--color-bg-input)',
          border:          '1px solid var(--color-border-subtle)',
        }}
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className="relative flex-1 py-2 transition-all duration-[150ms]"
              style={{
                fontFamily:      'var(--font-label)',
                fontSize:        'var(--text-label)',
                fontWeight:      600,
                letterSpacing:   'var(--tracking-label)',
                textTransform:   'uppercase',
                color:           isActive
                  ? 'var(--color-text-primary)'
                  : 'var(--color-text-muted)',
                backgroundColor: isActive
                  ? 'var(--color-bg-panel-raised)'
                  : 'transparent',
                clipPath: 'var(--chamfer-4)',
                outline:  'none',
              }}
            >
              {tab.label}
              {isActive && (
                <span
                  aria-hidden="true"
                  className="absolute bottom-0 left-0 right-0"
                  style={{
                    height:          2,
                    backgroundColor: 'var(--color-brand-orange)',
                  }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* ── Compliance items list ───────────────────────────────────────── */}
      <PlateCard
        header={TABS.find((t) => t.key === activeTab)?.label ?? activeTab}
        headerRight={
          <span className="micro-caps" style={{ color: 'var(--color-text-muted)' }}>
            {items.length} items
          </span>
        }
        accent="compliance"
        padding="none"
      >
        <div className="flex flex-col">
          {items.map((item) => (
            <ComplianceRow key={item.name} item={item} />
          ))}
        </div>
      </PlateCard>
    </AppShell>
  );
}
