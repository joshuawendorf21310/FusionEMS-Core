'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';
const POLL_INTERVAL_MS = 5000;

type ProvisioningStatus =
  | 'pending'
  | 'processing'
  | 'provisioning'
  | 'complete'
  | 'error'
  | string;

interface StatusResponse {
  application_id: string;
  provisioning_status: ProvisioningStatus;
  current_step?: string;
  step_detail?: string;
  progress_percent?: number;
  error_message?: string;
}

const STATUS_STEPS: { key: string; label: string }[] = [
  { key: 'pending',      label: 'Application Received' },
  { key: 'processing',   label: 'Verifying Payment'    },
  { key: 'provisioning', label: 'Provisioning Agency'  },
  { key: 'complete',     label: 'Ready'                },
];

function getStepIndex(status: ProvisioningStatus): number {
  const idx = STATUS_STEPS.findIndex(s => s.key === status);
  return idx === -1 ? 0 : idx;
}

function ProvisioningSteps({ status }: { status: ProvisioningStatus }) {
  const currentIdx = getStepIndex(status);
  const isError    = status === 'error';

  return (
    <div className="flex flex-col gap-2">
      {STATUS_STEPS.map((step, idx) => {
        const isDone    = !isError && idx < currentIdx;
        const isActive  = !isError && idx === currentIdx;
        const isPending = isError ? true : idx > currentIdx;

        return (
          <div key={step.key} className="flex items-center gap-3">
            {/* Icon */}
            <div
              className="flex-shrink-0 w-7 h-7 rounded-sm flex items-center justify-center"
              style={{
                backgroundColor: isDone
                  ? 'rgba(76,175,80,0.15)'
                  : isActive
                  ? 'rgba(255,107,26,0.15)'
                  : 'rgba(255,255,255,0.04)',
                border: isDone
                  ? '1px solid rgba(76,175,80,0.4)'
                  : isActive
                  ? '1px solid rgba(255,107,26,0.5)'
                  : '1px solid rgba(255,255,255,0.08)',
              }}
            >
              {isDone ? (
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M2 6l3 3 5-5" stroke="#4caf50" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : isActive ? (
                <svg className="animate-spin" width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="#ff6b1a" strokeWidth="4" />
                  <path className="opacity-75" fill="#ff6b1a" d="M4 12a8 8 0 018-8v8z" />
                </svg>
              ) : (
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: 'rgba(255,255,255,0.15)' }}
                />
              )}
            </div>

            {/* Label */}
            <span
              className="text-sm"
              style={{
                color: isDone
                  ? '#4caf50'
                  : isActive
                  ? '#ff8c42'
                  : isPending
                  ? 'rgba(255,255,255,0.25)'
                  : 'rgba(255,255,255,0.65)',
                fontWeight: isActive ? 600 : 400,
              }}
            >
              {step.label}
            </span>

            {isActive && (
              <span
                className="ml-1 text-xs px-1.5 py-0.5 rounded-sm"
                style={{
                  backgroundColor: 'rgba(255,107,26,0.12)',
                  border: '1px solid rgba(255,107,26,0.25)',
                  color: '#ff6b1a',
                }}
              >
                In progress
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function SuccessPage() {
  const router = useRouter();

  const [applicationId, setApplicationId] = useState('');
  const [agencyName,    setAgencyName]    = useState('');
  const [signerEmail,   setSignerEmail]   = useState('');

  const [statusData,  setStatusData]  = useState<StatusResponse | null>(null);
  const [pollError,   setPollError]   = useState('');
  const [isComplete,  setIsComplete]  = useState(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const poll = useCallback(async (appId: string) => {
    try {
      const res = await fetch(`${API_BASE}/public/onboarding/status/${appId}`);
      if (!res.ok) {
        let msg = `Status check failed (${res.status})`;
        try { const b = await res.json(); if (b?.detail) msg = b.detail; } catch {}
        setPollError(msg);
        return;
      }
      const data: StatusResponse = await res.json();
      setStatusData(data);
      setPollError('');

      if (data.provisioning_status === 'complete') {
        setIsComplete(true);
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
    } catch (err: unknown) {
      setPollError(err instanceof Error ? err.message : 'Unable to reach server.');
    }
  }, []);

  useEffect(() => {
    const appId      = localStorage.getItem('qs_app_id')       || '';
    const agency     = localStorage.getItem('qs_agency_name')  || '';
    const email      = localStorage.getItem('qs_signer_email') || '';

    setApplicationId(appId);
    setAgencyName(agency);
    setSignerEmail(email);

    if (!appId) return;

    // Initial poll
    poll(appId);

    // Recurring poll
    intervalRef.current = setInterval(() => poll(appId), POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [poll]);

  const currentStatus: ProvisioningStatus = statusData?.provisioning_status || 'pending';
  const progress = statusData?.progress_percent ?? (isComplete ? 100 : undefined);

  return (
    <div
      className="rounded-sm border p-6 md:p-8"
      style={{ backgroundColor: '#0b0f14', borderColor: 'rgba(255,255,255,0.08)' }}
    >
      {/* Top success banner */}
      <div
        className="rounded-sm border px-5 py-4 mb-6 flex items-start gap-4"
        style={{
          backgroundColor: isComplete ? 'rgba(76,175,80,0.08)' : 'rgba(255,107,26,0.06)',
          borderColor:     isComplete ? 'rgba(76,175,80,0.3)'  : 'rgba(255,107,26,0.2)',
        }}
      >
        <div
          className="flex-shrink-0 w-10 h-10 rounded-sm flex items-center justify-center mt-0.5"
          style={{
            backgroundColor: isComplete ? 'rgba(76,175,80,0.15)' : 'rgba(255,107,26,0.15)',
            border: isComplete ? '1px solid rgba(76,175,80,0.4)' : '1px solid rgba(255,107,26,0.4)',
          }}
        >
          {isComplete ? (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M3 10l5 5 9-9" stroke="#4caf50" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ) : (
            <svg className="animate-spin" width="20" height="20" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="#ff6b1a" strokeWidth="4" />
              <path className="opacity-75" fill="#ff6b1a" d="M4 12a8 8 0 018-8v8z" />
            </svg>
          )}
        </div>
        <div>
          <h1
            className="text-base font-bold text-white uppercase tracking-wider"
            style={{ fontFamily: "'Barlow Condensed', 'Barlow', sans-serif" }}
          >
            {isComplete ? 'Agency Provisioned!' : 'Your Agency is Being Provisioned'}
          </h1>
          <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.5)' }}>
            {isComplete
              ? 'Your FusionEMS Quantum environment is ready.'
              : 'This typically takes about 2 minutes. You can leave this page — we&apos;ll send login credentials to your email.'}
          </p>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        {/* Left: Provisioning steps */}
        <div
          className="rounded-sm border p-5"
          style={{ backgroundColor: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.08)' }}
        >
          <div
            className="text-xs font-semibold uppercase tracking-wider mb-4"
            style={{ color: 'rgba(255,255,255,0.4)' }}
          >
            Provisioning Status
          </div>
          <ProvisioningSteps status={currentStatus} />

          {/* Progress bar */}
          {progress !== undefined && (
            <div className="mt-5">
              <div
                className="flex justify-between text-xs mb-1"
                style={{ color: 'rgba(255,255,255,0.3)' }}
              >
                <span>Progress</span>
                <span>{progress}%</span>
              </div>
              <div
                className="w-full rounded-full overflow-hidden"
                style={{ height: '4px', backgroundColor: 'rgba(255,255,255,0.06)' }}
              >
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${progress}%`,
                    backgroundColor: isComplete ? '#4caf50' : '#ff6b1a',
                  }}
                />
              </div>
            </div>
          )}

          {/* Current step detail */}
          {statusData?.current_step && (
            <div
              className="mt-3 text-xs px-2.5 py-1.5 rounded-sm"
              style={{
                backgroundColor: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.06)',
                color: 'rgba(255,255,255,0.45)',
              }}
            >
              {statusData.step_detail || statusData.current_step}
            </div>
          )}

          {/* Poll error */}
          {pollError && (
            <div
              className="mt-3 text-xs px-2.5 py-1.5 rounded-sm"
              style={{
                backgroundColor: 'rgba(255,59,59,0.06)',
                border: '1px solid rgba(255,59,59,0.2)',
                color: '#ff6b6b',
              }}
            >
              {pollError} — retrying…
            </div>
          )}

          {/* Polling indicator */}
          {!isComplete && !pollError && (
            <div className="mt-4 flex items-center gap-2">
              <div
                className="w-1.5 h-1.5 rounded-full animate-pulse"
                style={{ backgroundColor: '#22d3ee' }}
              />
              <span className="text-xs" style={{ color: 'rgba(255,255,255,0.25)' }}>
                Checking every {POLL_INTERVAL_MS / 1000}s…
              </span>
            </div>
          )}
        </div>

        {/* Right: Info panel */}
        <div
          className="rounded-sm border p-5"
          style={{ backgroundColor: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.08)' }}
        >
          <div
            className="text-xs font-semibold uppercase tracking-wider mb-4"
            style={{ color: 'rgba(255,255,255,0.4)' }}
          >
            What Happens Next
          </div>
          <div className="space-y-3">
            {[
              {
                icon: (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" stroke="#22d3ee" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ),
                text: `Login credentials will be sent to ${signerEmail || 'your email'}.`,
              },
              {
                icon: (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="#ff6b1a" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ),
                text: 'Your HIPAA-compliant tenant is being isolated and configured.',
              },
              {
                icon: (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="#4caf50" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ),
                text: 'NEMSIS & ePCR modules will be pre-configured for your state.',
              },
              {
                icon: (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0" stroke="#22d3ee" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ),
                text: 'Onboarding support will reach out within one business day.',
              },
            ].map((item, idx) => (
              <div key={idx} className="flex items-start gap-3">
                <div
                  className="flex-shrink-0 w-6 h-6 rounded-sm flex items-center justify-center mt-0.5"
                  style={{
                    backgroundColor: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.08)',
                  }}
                >
                  {item.icon}
                </div>
                <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.55)' }}>
                  {item.text}
                </p>
              </div>
            ))}
          </div>

          {/* Agency info */}
          {agencyName && (
            <div
              className="mt-4 pt-4 border-t"
              style={{ borderColor: 'rgba(255,255,255,0.06)' }}
            >
              <div className="text-xs" style={{ color: 'rgba(255,255,255,0.25)' }}>
                Agency
              </div>
              <div className="text-sm font-semibold text-white mt-0.5">{agencyName}</div>
            </div>
          )}

          {applicationId && (
            <div className="mt-2">
              <div className="text-xs" style={{ color: 'rgba(255,255,255,0.25)' }}>
                Application ID
              </div>
              <div
                className="text-xs font-mono mt-0.5"
                style={{ color: 'rgba(255,255,255,0.35)' }}
              >
                {applicationId}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Provisioning error */}
      {currentStatus === 'error' && statusData?.error_message && (
        <div
          className="rounded-sm border px-4 py-3 text-sm mb-5"
          style={{
            backgroundColor: 'rgba(255,59,59,0.08)',
            borderColor: 'rgba(255,59,59,0.3)',
            color: '#ff6b6b',
          }}
        >
          <span className="font-semibold">Provisioning Error: </span>
          {statusData.error_message}
        </div>
      )}

      {/* CTA */}
      <div
        className="pt-5 border-t flex items-center justify-between"
        style={{ borderColor: 'rgba(255,255,255,0.06)' }}
      >
        <p className="text-xs" style={{ color: 'rgba(255,255,255,0.25)' }}>
          {isComplete
            ? 'Your account is ready. Welcome to FusionEMS Quantum.'
            : 'Provisioning is automatic — this page will update when complete.'}
        </p>
        {isComplete ? (
          <button
            onClick={() => router.push('/login')}
            className="bg-[#ff6b1a] text-black font-bold px-6 py-2.5 text-sm uppercase tracking-wider hover:bg-[#ff8c42] transition-colors rounded-sm"
          >
            Login Now →
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full animate-pulse"
              style={{ backgroundColor: '#ff6b1a' }}
            />
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#ff6b1a' }}>
              Provisioning…
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
