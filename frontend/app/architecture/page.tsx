'use client';

import AppShell from '@/components/AppShell';

const LAYERS = [
  {
    id: 'edge',
    number: '01',
    label: 'Edge & CDN',
    accent: 'var(--color-system-cad)',
    services: [
      'CloudFront Distribution',
      'AWS WAF',
      'ACM Certificates',
      'Route 53 DNS',
      'Shield Standard',
    ],
  },
  {
    id: 'application',
    number: '02',
    label: 'Application',
    accent: 'var(--color-brand-orange)',
    services: [
      'ECS Fargate — API Cluster',
      'ECS Fargate — Worker Cluster',
      'Application Load Balancer',
      'WebSocket Server',
      'Task Scheduler',
    ],
  },
  {
    id: 'data',
    number: '03',
    label: 'Data',
    accent: 'var(--color-system-billing)',
    services: [
      'RDS Aurora PostgreSQL (Multi-AZ)',
      'ElastiCache Redis',
      'S3 — PHI Encrypted',
      'S3 — Document Store',
      'DynamoDB — Session Cache',
    ],
  },
  {
    id: 'observability',
    number: '04',
    label: 'Observability & Security',
    accent: 'var(--color-system-compliance)',
    services: [
      'CloudWatch Logs & Metrics',
      'AWS X-Ray Tracing',
      'OPA Policy Engine',
      'Secrets Manager',
      'CloudTrail Audit',
      'GuardDuty',
    ],
  },
];

const INFRA_SPECS = [
  { label: 'Region', value: 'us-east-1' },
  { label: 'ECS vCPU', value: '4' },
  { label: 'ECS Memory', value: '8 GB' },
  { label: 'RDS Instance', value: 'db.r6g.large' },
  { label: 'Redis', value: 'cache.t4g.medium' },
  { label: 'CloudFront PoPs', value: '450+' },
];

const SECURITY_POSTURE = [
  'Encryption at rest (AES-256)',
  'Encryption in transit (TLS 1.3)',
  'VPC isolation',
  'WAF rules active',
  'OPA policy enforcement',
  'MFA required',
  'PHI access logging',
  'SOC2-aligned controls',
];

export default function ArchitecturePage() {
  return (
    <AppShell>
      {/* Page Header */}
      <div
        className="hud-rail pb-4 mb-8"
        style={{ borderBottom: '1px solid var(--color-border-default)' }}
      >
        <p
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
          Infrastructure
        </p>
        <h1
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 'var(--text-h1)',
            fontWeight: 700,
            color: 'var(--color-text-primary)',
            lineHeight: 'var(--leading-tight)',
          }}
        >
          Platform Architecture
        </h1>
        <p
          style={{
            fontSize: 'var(--text-body)',
            color: 'var(--color-text-muted)',
            marginTop: 4,
          }}
        >
          FusionEMS Quantum infrastructure topology
        </p>
      </div>

      {/* Architecture Layers */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 40 }}>
        {LAYERS.map((layer, idx) => (
          <div
            key={layer.id}
            style={{
              background: 'var(--color-bg-panel)',
              border: '1px solid var(--color-border-default)',
              borderLeft: `3px solid ${layer.accent}`,
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
              padding: '16px 20px 16px 20px',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                marginBottom: 12,
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 10,
                  color: layer.accent,
                  opacity: 0.7,
                  letterSpacing: '0.1em',
                  minWidth: 24,
                }}
              >
                {layer.number}
              </span>
              <span
                style={{
                  fontFamily: 'var(--font-label)',
                  fontSize: 'var(--text-label)',
                  fontWeight: 600,
                  letterSpacing: 'var(--tracking-label)',
                  textTransform: 'uppercase',
                  color: layer.accent,
                }}
              >
                {layer.label}
              </span>
              <div
                style={{
                  flex: 1,
                  height: 1,
                  background: `linear-gradient(90deg, ${layer.accent}33, transparent)`,
                }}
              />
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {layer.services.map((svc) => (
                <div
                  key={svc}
                  style={{
                    background: 'var(--color-bg-overlay)',
                    border: `1px solid ${layer.accent}22`,
                    clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
                    padding: '4px 10px',
                    fontSize: 11,
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--color-text-secondary)',
                    letterSpacing: '0.02em',
                  }}
                >
                  {svc}
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Connector arrows between layers */}
      </div>

      {/* Two-column info section */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: 16,
        }}
      >
        {/* Infrastructure Specs */}
        <div
          style={{
            background: 'var(--color-bg-panel)',
            border: '1px solid var(--color-border-default)',
            clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
          }}
        >
          <div
            className="hud-rail"
            style={{
              padding: '12px 16px',
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
                color: 'var(--color-text-secondary)',
              }}
            >
              Infrastructure Specs
            </span>
          </div>
          <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                {INFRA_SPECS.map((spec) => (
                  <tr
                    key={spec.label}
                    style={{ borderBottom: '1px solid var(--color-border-subtle)' }}
                  >
                    <td
                      style={{
                        padding: '10px 0',
                        fontSize: 'var(--text-label)',
                        fontFamily: 'var(--font-label)',
                        fontWeight: 600,
                        letterSpacing: 'var(--tracking-label)',
                        textTransform: 'uppercase',
                        color: 'var(--color-text-muted)',
                        width: '50%',
                      }}
                    >
                      {spec.label}
                    </td>
                    <td
                      style={{
                        padding: '10px 0',
                        fontSize: 'var(--text-body)',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--color-text-primary)',
                        textAlign: 'right',
                      }}
                    >
                      {spec.value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Security Posture */}
        <div
          style={{
            background: 'var(--color-bg-panel)',
            border: '1px solid var(--color-border-default)',
            clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
          }}
        >
          <div
            className="hud-rail"
            style={{
              padding: '12px 16px',
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
                color: 'var(--color-text-secondary)',
              }}
            >
              Security Posture
            </span>
          </div>
          <div style={{ padding: '8px 16px 16px' }}>
            {SECURITY_POSTURE.map((item) => (
              <div
                key={item}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '8px 0',
                  borderBottom: '1px solid var(--color-border-subtle)',
                }}
              >
                <div
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: '50%',
                    background: 'rgba(76, 175, 80, 0.15)',
                    border: '1px solid var(--color-status-active)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    fontSize: 10,
                    color: 'var(--color-status-active)',
                    fontWeight: 700,
                  }}
                >
                  ✓
                </div>
                <span
                  style={{
                    fontSize: 'var(--text-body)',
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  {item}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
