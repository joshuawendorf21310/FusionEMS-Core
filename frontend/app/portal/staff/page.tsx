'use client';

import AppShell from '@/components/AppShell';

const PANEL_STYLE = {
  clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
  background: 'var(--color-bg-panel, #0f1720)',
  border: '1px solid rgba(255,255,255,0.08)',
};

const LABEL_STYLE: React.CSSProperties = {
  fontSize: '0.75rem',
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: 'rgba(255,255,255,0.4)',
};

type Priority = 'HIGH' | 'MED' | 'LOW';

interface Claim {
  id: string;
  patientId: string;
  dos: string;
  payer: string;
  amount: string;
  priority: Priority;
}

interface Activity {
  time: string;
  text: string;
}

const SAMPLE_CLAIMS: Claim[] = [
  { id: 'CLM-88412', patientId: 'PT-***4821', dos: '02/14/2026', payer: 'BlueCross BS', amount: '$1,842.00', priority: 'HIGH' },
  { id: 'CLM-88398', patientId: 'PT-***1193', dos: '02/13/2026', payer: 'Aetna', amount: '$3,210.50', priority: 'HIGH' },
  { id: 'CLM-88375', patientId: 'PT-***7742', dos: '02/12/2026', payer: 'United Health', amount: '$970.00', priority: 'MED' },
  { id: 'CLM-88361', patientId: 'PT-***3309', dos: '02/11/2026', payer: 'Cigna', amount: '$2,150.75', priority: 'MED' },
  { id: 'CLM-88349', patientId: 'PT-***9954', dos: '02/10/2026', payer: 'Medicare', amount: '$680.00', priority: 'LOW' },
  { id: 'CLM-88337', patientId: 'PT-***6618', dos: '02/09/2026', payer: 'Medicaid', amount: '$455.25', priority: 'LOW' },
  { id: 'CLM-88321', patientId: 'PT-***2287', dos: '02/08/2026', payer: 'BlueCross BS', amount: '$5,320.00', priority: 'HIGH' },
  { id: 'CLM-88308', patientId: 'PT-***8801', dos: '02/07/2026', payer: 'Humana', amount: '$1,090.00', priority: 'MED' },
];

const RECENT_ACTIVITY: Activity[] = [
  { time: '09:42 AM', text: 'CLM-88412 submitted to BlueCross BS' },
  { time: '09:28 AM', text: 'Denial worked on CLM-88276 — resubmitted' },
  { time: '09:11 AM', text: 'Payment posted: CLM-88194 · $2,340.00' },
  { time: '08:55 AM', text: 'Auth rep document approved — PT-***4821' },
  { time: '08:39 AM', text: 'CLM-88398 flagged for additional documentation' },
  { time: '08:22 AM', text: 'Batch upload completed: 14 claims processed' },
];

const PRIORITY_STYLE: Record<Priority, React.CSSProperties> = {
  HIGH: {
    background: 'rgba(220,38,38,0.15)',
    border: '1px solid rgba(220,38,38,0.35)',
    color: '#f87171',
  },
  MED: {
    background: 'rgba(234,179,8,0.12)',
    border: '1px solid rgba(234,179,8,0.3)',
    color: '#fde047',
  },
  LOW: {
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.1)',
    color: 'rgba(255,255,255,0.45)',
  },
};

function PriorityChip({ priority }: { priority: Priority }) {
  return (
    <span
      style={{
        ...PRIORITY_STYLE[priority],
        fontSize: '0.6875rem',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        padding: '2px 8px',
        clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)',
        fontWeight: 600,
        display: 'inline-block',
      }}
    >
      {priority}
    </span>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
}

function StatCard({ label, value, sub }: StatCardProps) {
  return (
    <div style={{ ...PANEL_STYLE, padding: '18px 20px', flex: 1, minWidth: 0 }}>
      <p style={{ ...LABEL_STYLE, margin: '0 0 8px' }}>{label}</p>
      <p style={{ color: '#fff', fontSize: '1.75rem', fontWeight: 700, margin: '0 0 2px', lineHeight: 1 }}>{value}</p>
      {sub && <p style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.75rem', margin: 0 }}>{sub}</p>}
    </div>
  );
}

export default function StaffDashboardPage() {
  return (
    <AppShell>
      <div style={{ background: 'var(--color-bg-base, #0b0f14)', minHeight: 'calc(100vh - 120px)' }}>
        {/* Page header */}
        <div style={{ marginBottom: '28px' }}>
          <h1 style={{ color: '#fff', fontSize: '1.5rem', fontWeight: 700, margin: '0 0 4px' }}>
            Staff Dashboard
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.875rem', margin: 0 }}>
            Billing Specialist
          </p>
        </div>

        {/* Top stats */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
          <StatCard label="My Open Claims" value="34" sub="across 8 payers" />
          <StatCard label="Claims Due Today" value="7" sub="by 5:00 PM" />
          <StatCard label="Pending Authorizations" value="5" sub="awaiting approval" />
          <StatCard label="Flagged for Review" value="3" sub="require action" />
        </div>

        {/* Main content: queue + activity */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '16px', alignItems: 'start' }}>
          {/* Claims queue */}
          <div style={{ ...PANEL_STYLE, overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              <p style={{ ...LABEL_STYLE, margin: 0 }}>My Claims Queue</p>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Claim ID', 'Patient ID', 'DOS', 'Payer', 'Amount', 'Priority', 'Action'].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: '10px 16px',
                          textAlign: 'left',
                          fontSize: '0.6875rem',
                          letterSpacing: '0.08em',
                          textTransform: 'uppercase',
                          color: 'rgba(255,255,255,0.35)',
                          fontWeight: 600,
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {SAMPLE_CLAIMS.map((claim, i) => (
                    <tr
                      key={claim.id}
                      style={{
                        borderBottom: i < SAMPLE_CLAIMS.length - 1 ? '1px solid rgba(255,255,255,0.04)' : undefined,
                        background: i % 2 === 1 ? 'rgba(255,255,255,0.015)' : undefined,
                      }}
                    >
                      <td style={{ padding: '12px 16px', color: '#fff', fontSize: '0.875rem', fontWeight: 500, whiteSpace: 'nowrap' }}>
                        {claim.id}
                      </td>
                      <td style={{ padding: '12px 16px', color: 'rgba(255,255,255,0.5)', fontSize: '0.875rem', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                        {claim.patientId}
                      </td>
                      <td style={{ padding: '12px 16px', color: 'rgba(255,255,255,0.6)', fontSize: '0.875rem', whiteSpace: 'nowrap' }}>
                        {claim.dos}
                      </td>
                      <td style={{ padding: '12px 16px', color: 'rgba(255,255,255,0.6)', fontSize: '0.875rem', whiteSpace: 'nowrap' }}>
                        {claim.payer}
                      </td>
                      <td style={{ padding: '12px 16px', color: 'rgba(255,255,255,0.85)', fontSize: '0.875rem', fontWeight: 600, whiteSpace: 'nowrap' }}>
                        {claim.amount}
                      </td>
                      <td style={{ padding: '12px 16px', whiteSpace: 'nowrap' }}>
                        <PriorityChip priority={claim.priority} />
                      </td>
                      <td style={{ padding: '12px 16px', whiteSpace: 'nowrap' }}>
                        <button
                          type="button"
                          style={{
                            background: 'rgba(255,107,26,0.1)',
                            border: '1px solid rgba(255,107,26,0.25)',
                            clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
                            color: '#ff6b1a',
                            fontSize: '0.75rem',
                            letterSpacing: '0.06em',
                            textTransform: 'uppercase',
                            padding: '4px 12px',
                            cursor: 'pointer',
                            fontWeight: 600,
                          }}
                        >
                          Work
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent activity */}
          <div style={{ ...PANEL_STYLE, overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              <p style={{ ...LABEL_STYLE, margin: 0 }}>Recent Activity</p>
            </div>
            <div style={{ padding: '8px 0' }}>
              {RECENT_ACTIVITY.map((a, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    gap: '12px',
                    padding: '12px 18px',
                    borderBottom: i < RECENT_ACTIVITY.length - 1 ? '1px solid rgba(255,255,255,0.04)' : undefined,
                    alignItems: 'flex-start',
                  }}
                >
                  <div
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: 'rgba(255,107,26,0.6)',
                      marginTop: '6px',
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ minWidth: 0 }}>
                    <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.8125rem', margin: '0 0 2px', lineHeight: 1.4 }}>
                      {a.text}
                    </p>
                    <p style={{ color: 'rgba(255,255,255,0.25)', fontSize: '0.6875rem', margin: 0 }}>
                      {a.time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom stats */}
        <div style={{ display: 'flex', gap: '12px', marginTop: '16px', flexWrap: 'wrap' }}>
          <StatCard label="Claims Processed Today" value="18" sub="as of 09:42 AM" />
          <StatCard label="Clean Claim Rate" value="91.2%" sub="last 30 days" />
          <StatCard label="Avg Processing Time" value="2.4d" sub="last 30 days" />
          <StatCard label="Denials Worked" value="6" sub="this week" />
        </div>
      </div>
    </AppShell>
  );
}
