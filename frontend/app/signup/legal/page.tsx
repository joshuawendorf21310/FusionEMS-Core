'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

const inputClass =
  'bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm text-white placeholder-[rgba(255,255,255,0.3)] focus:outline-none focus:border-[#ff6b1a] rounded-sm w-full';

const MSA_SUMMARY = `MASTER SERVICE AGREEMENT — KEY TERMS SUMMARY

1. SUBSCRIPTION & ACCESS
FusionEMS Quantum ("Platform") is provided as a software-as-a-service subscription. Access is granted to authorized agency personnel only. Licenses are non-transferable.

2. PAYMENT & BILLING
Subscription fees are billed monthly or annually as selected at checkout. All fees are non-refundable except as stated in the Refund Policy. FusionEMS Quantum reserves the right to suspend access upon non-payment after a 10-day grace period.

3. ACCEPTABLE USE
The Platform may only be used for lawful EMS dispatch, billing, records management, and related agency operations. Reverse engineering, data scraping, or resale of the Platform is strictly prohibited.

4. DATA OWNERSHIP
Agency data remains the exclusive property of the subscribing agency. FusionEMS Quantum is granted a limited license to process agency data solely for the purpose of providing the Platform services.

5. INTELLECTUAL PROPERTY
The Platform, including all software, interfaces, documentation, and underlying technology, is the exclusive intellectual property of FusionEMS Quantum and its licensors.

6. CONFIDENTIALITY
Both parties agree to maintain the confidentiality of the other party's proprietary information and to use such information only as necessary to fulfill their obligations under this Agreement.

7. LIMITATION OF LIABILITY
IN NO EVENT SHALL FUSIONEMS QUANTUM BE LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES. TOTAL LIABILITY SHALL NOT EXCEED FEES PAID IN THE 12 MONTHS PRECEDING THE CLAIM.

8. TERM & TERMINATION
This Agreement commences on the date of electronic execution and continues for the initial subscription term. Either party may terminate for material breach with 30 days written notice and opportunity to cure.

9. GOVERNING LAW
This Agreement is governed by the laws of the State of Delaware, without regard to conflict-of-law principles.`;

const BAA_SUMMARY = `HIPAA BUSINESS ASSOCIATE AGREEMENT — KEY TERMS SUMMARY

1. DEFINITIONS
"Covered Entity" means the subscribing EMS agency. "Business Associate" means FusionEMS Quantum. "PHI" means Protected Health Information as defined under HIPAA (45 CFR §160.103).

2. PERMITTED USES
Business Associate may use and disclose PHI only as necessary to provide the contracted services, as required by law, or as otherwise permitted under this BAA and HIPAA regulations.

3. SAFEGUARDS
Business Associate agrees to implement administrative, physical, and technical safeguards to protect the confidentiality, integrity, and availability of ePHI in accordance with 45 CFR Part 164 Subpart C.

4. SUBCONTRACTORS
Business Associate will ensure that any subcontractors or agents that handle PHI agree to the same restrictions and conditions as those in this BAA.

5. BREACH NOTIFICATION
Business Associate will notify Covered Entity of any discovered Breach of Unsecured PHI without unreasonable delay and in no case later than 60 days after discovery, per 45 CFR §164.410.

6. ACCESS & AMENDMENT
Business Associate will make PHI available to Covered Entity for amendment and provide an accounting of disclosures as required under 45 CFR §§164.524 and 164.526.

7. TERM & TERMINATION
This BAA is effective as of the date of electronic execution. Upon termination, Business Associate will return or destroy all PHI, if feasible, or continue protecting PHI that cannot be returned or destroyed.

8. COMPLIANCE
Both parties agree to comply with all applicable requirements of HIPAA, the HITECH Act, and any applicable state privacy laws.`;

function Highlight({ children }: { children: React.ReactNode }) {
  return (
    <span style={{ color: '#22d3ee', fontWeight: 600 }}>{children}</span>
  );
}

function processDocText(text: string): React.ReactNode[] {
  const highlights = [
    'FusionEMS Quantum', 'PHI', 'ePHI', 'Protected Health Information',
    'HIPAA', 'HITECH', 'Business Associate', 'Covered Entity',
    'non-refundable', 'non-transferable', 'strictly prohibited',
    'Breach', 'safeguards', 'confidentiality',
  ];
  const pattern = new RegExp(`(${highlights.map(h => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'g');

  return text.split('\n').map((line, li) => {
    if (/^\d+\.\s+[A-Z]/.test(line)) {
      return (
        <p key={li} className="mt-3 mb-1 text-xs font-bold uppercase tracking-wider" style={{ color: '#ff6b1a' }}>
          {line}
        </p>
      );
    }
    const parts = line.split(pattern);
    return (
      <p key={li} className="text-xs leading-relaxed mb-1" style={{ color: 'rgba(255,255,255,0.65)' }}>
        {parts.map((part, pi) =>
          highlights.includes(part) ? <Highlight key={pi}>{part}</Highlight> : part
        )}
      </p>
    );
  });
}

export default function LegalPage() {
  const router = useRouter();

  const [packetId,    setPacketId]   = useState<string | null>(null);
  const [initError,   setInitError]  = useState('');
  const [initLoading, setInitLoading] = useState(true);

  const [checkedMSA,  setCheckedMSA]  = useState(false);
  const [checkedBAA,  setCheckedBAA]  = useState(false);
  const [checkedAuth, setCheckedAuth] = useState(false);
  const [sigText,     setSigText]     = useState('');
  const [sigError,    setSigError]    = useState('');
  const [apiError,    setApiError]    = useState('');
  const [signing,     setSigning]     = useState(false);
  const [signerName,  setSignerName]  = useState('');

  const msaRef = useRef<HTMLDivElement>(null);
  const baaRef = useRef<HTMLDivElement>(null);

  // Create legal packet on mount
  useEffect(() => {
    const applicationId = localStorage.getItem('qs_app_id')       || '';
    const signerEmail   = localStorage.getItem('qs_signer_email') || '';
    const name          = localStorage.getItem('qs_signer_name')  || '';
    const agencyName    = localStorage.getItem('qs_agency_name')  || '';

    setSignerName(name);

    if (!applicationId) {
      setInitError('No application ID found. Please restart the signup process.');
      setInitLoading(false);
      return;
    }

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/public/onboarding/legal/packet/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            application_id: applicationId,
            signer_email:   signerEmail,
            signer_name:    name,
            agency_name:    agencyName,
          }),
        });

        if (!res.ok) {
          let msg = `Error ${res.status}: ${res.statusText}`;
          try {
            const body = await res.json();
            if (body?.detail) msg = body.detail;
          } catch {}
          throw new Error(msg);
        }

        const data = await res.json();
        const pid = data?.packet_id || data?.id || '';
        if (!pid) throw new Error('No packet ID returned from server.');
        setPacketId(pid);
      } catch (err: unknown) {
        setInitError(err instanceof Error ? err.message : 'Failed to initialize legal packet.');
      } finally {
        setInitLoading(false);
      }
    })();
  }, []);

  const handleSign = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setSigError('');
      setApiError('');

      if (!checkedMSA)  { setSigError('You must agree to the Master Service Agreement.'); return; }
      if (!checkedBAA)  { setSigError('You must agree to the Business Associate Agreement.'); return; }
      if (!checkedAuth) { setSigError('You must certify your authority to sign.'); return; }
      if (!sigText.trim()) { setSigError('Type your full legal name to sign.'); return; }

      if (!packetId) {
        setApiError('Legal packet is not ready. Please refresh and try again.');
        return;
      }

      setSigning(true);
      try {
        // Get IP address
        let ipAddress = 'unknown';
        try {
          const ipRes = await fetch('https://api.ipify.org?format=json');
          const ipData = await ipRes.json();
          ipAddress = ipData.ip || 'unknown';
        } catch {}

        const res = await fetch(`${API_BASE}/public/onboarding/legal/packet/${packetId}/sign`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            signer_name:    signerName || sigText.trim(),
            consents: {
              msa:       checkedMSA,
              baa:       checkedBAA,
              authority: checkedAuth,
            },
            ip_address:     ipAddress,
            user_agent:     navigator.userAgent,
            signature_text: sigText.trim(),
          }),
        });

        if (!res.ok) {
          let msg = `Error ${res.status}: ${res.statusText}`;
          try {
            const body = await res.json();
            if (body?.detail) msg = body.detail;
          } catch {}
          throw new Error(msg);
        }

        router.push('/signup/checkout');
      } catch (err: unknown) {
        setApiError(err instanceof Error ? err.message : 'An unexpected error occurred.');
      } finally {
        setSigning(false);
      }
    },
    [checkedMSA, checkedBAA, checkedAuth, sigText, packetId, signerName, router]
  );

  if (initLoading) {
    return (
      <div
        className="rounded-sm border p-8 flex flex-col items-center justify-center gap-4"
        style={{ backgroundColor: '#0b0f14', borderColor: 'rgba(255,255,255,0.08)', minHeight: '300px' }}
      >
        <svg className="animate-spin h-8 w-8" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="#ff6b1a" strokeWidth="4" />
          <path className="opacity-75" fill="#ff6b1a" d="M4 12a8 8 0 018-8v8z" />
        </svg>
        <p className="text-sm" style={{ color: 'rgba(255,255,255,0.45)' }}>
          Preparing your legal packet…
        </p>
      </div>
    );
  }

  if (initError) {
    return (
      <div
        className="rounded-sm border p-8"
        style={{ backgroundColor: '#0b0f14', borderColor: 'rgba(255,255,255,0.08)' }}
      >
        <div
          className="rounded-sm border px-4 py-3 text-sm"
          style={{
            backgroundColor: 'rgba(255,59,59,0.08)',
            borderColor: 'rgba(255,59,59,0.3)',
            color: '#ff6b6b',
          }}
        >
          <span className="font-semibold">Error: </span>{initError}
        </div>
        <button
          onClick={() => router.push('/signup')}
          className="mt-4 text-sm underline"
          style={{ color: '#ff6b1a' }}
        >
          ← Restart signup
        </button>
      </div>
    );
  }

  return (
    <div
      className="rounded-sm border p-6 md:p-8"
      style={{ backgroundColor: '#0b0f14', borderColor: 'rgba(255,255,255,0.08)' }}
    >
      {/* Header */}
      <div className="mb-6 border-b pb-5" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <h1
          className="text-xl font-bold uppercase tracking-wider text-white"
          style={{ fontFamily: "'Barlow Condensed', 'Barlow', sans-serif" }}
        >
          Legal Agreements
        </h1>
        <p className="mt-1 text-sm" style={{ color: 'rgba(255,255,255,0.45)' }}>
          Please read and acknowledge the following agreements before proceeding.
        </p>
      </div>

      {/* Packet status badge */}
      <div className="mb-5 flex items-center gap-2">
        <div
          className="rounded-sm px-2.5 py-1 text-xs font-bold uppercase tracking-wider"
          style={{
            backgroundColor: 'rgba(34,211,238,0.1)',
            border: '1px solid rgba(34,211,238,0.25)',
            color: '#22d3ee',
          }}
        >
          Packet Ready
        </div>
        <span className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
          ID: {packetId}
        </span>
      </div>

      {/* MSA Document */}
      <div className="mb-5">
        <div
          className="mb-2 flex items-center justify-between text-xs font-semibold uppercase tracking-wider"
          style={{ color: 'rgba(255,255,255,0.55)' }}
        >
          <span>Master Service Agreement</span>
          <span style={{ color: 'rgba(255,255,255,0.25)' }}>Scroll to read</span>
        </div>
        <div
          ref={msaRef}
          className="rounded-sm border p-4 overflow-y-auto"
          style={{
            backgroundColor: 'rgba(255,255,255,0.02)',
            borderColor: 'rgba(255,255,255,0.08)',
            maxHeight: '200px',
          }}
        >
          {processDocText(MSA_SUMMARY)}
        </div>
      </div>

      {/* BAA Document */}
      <div className="mb-6">
        <div
          className="mb-2 flex items-center justify-between text-xs font-semibold uppercase tracking-wider"
          style={{ color: 'rgba(255,255,255,0.55)' }}
        >
          <span>HIPAA Business Associate Agreement</span>
          <span style={{ color: 'rgba(255,255,255,0.25)' }}>Scroll to read</span>
        </div>
        <div
          ref={baaRef}
          className="rounded-sm border p-4 overflow-y-auto"
          style={{
            backgroundColor: 'rgba(255,255,255,0.02)',
            borderColor: 'rgba(255,255,255,0.08)',
            maxHeight: '200px',
          }}
        >
          {processDocText(BAA_SUMMARY)}
        </div>
      </div>

      {/* API Error Banner */}
      {apiError && (
        <div
          className="mb-5 rounded-sm border px-4 py-3 text-sm"
          style={{
            backgroundColor: 'rgba(255,59,59,0.08)',
            borderColor: 'rgba(255,59,59,0.3)',
            color: '#ff6b6b',
          }}
        >
          <span className="font-semibold">Error: </span>{apiError}
        </div>
      )}

      <form onSubmit={handleSign} noValidate>
        {/* Checkboxes */}
        <div
          className="rounded-sm border p-4 mb-5 space-y-3"
          style={{
            backgroundColor: 'rgba(255,255,255,0.02)',
            borderColor: 'rgba(255,255,255,0.08)',
          }}
        >
          {[
            {
              id: 'msa',
              checked: checkedMSA,
              set: setCheckedMSA,
              label: 'I have read and agree to the Master Service Agreement',
            },
            {
              id: 'baa',
              checked: checkedBAA,
              set: setCheckedBAA,
              label: 'I have read and agree to the HIPAA Business Associate Agreement',
            },
            {
              id: 'auth',
              checked: checkedAuth,
              set: setCheckedAuth,
              label: 'I certify that I am authorized to sign on behalf of the agency',
            },
          ].map(item => (
            <label key={item.id} className="flex items-start gap-3 cursor-pointer group">
              <div className="relative flex-shrink-0 mt-0.5">
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={item.checked}
                  onChange={e => item.set(e.target.checked)}
                  disabled={signing}
                />
                <div
                  className="w-4 h-4 rounded-sm border flex items-center justify-center transition-colors"
                  style={{
                    backgroundColor: item.checked ? '#ff6b1a' : 'rgba(255,255,255,0.05)',
                    borderColor: item.checked ? '#ff6b1a' : 'rgba(255,255,255,0.2)',
                  }}
                >
                  {item.checked && (
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                      <path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="black" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>
              </div>
              <span className="text-sm" style={{ color: item.checked ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.55)' }}>
                {item.label}
              </span>
            </label>
          ))}
        </div>

        {/* Signature */}
        <div className="mb-5">
          <label
            className="block text-xs font-semibold mb-1.5 uppercase tracking-wider"
            style={{ color: 'rgba(255,255,255,0.55)' }}
          >
            Electronic Signature <span style={{ color: '#ff6b1a' }}>*</span>
          </label>
          <p className="text-xs mb-2" style={{ color: 'rgba(255,255,255,0.35)' }}>
            Type your full legal name exactly as it appears on your account to sign.
          </p>
          <input
            type="text"
            className={inputClass}
            placeholder={signerName || 'Your full legal name'}
            value={sigText}
            onChange={e => { setSigText(e.target.value); setSigError(''); }}
            disabled={signing}
          />
          {sigText && (
            <div
              className="mt-2 px-3 py-2 rounded-sm border text-sm italic"
              style={{
                backgroundColor: 'rgba(255,107,26,0.04)',
                borderColor: 'rgba(255,107,26,0.2)',
                color: '#ff8c42',
                fontFamily: 'Georgia, serif',
                fontSize: '15px',
              }}
            >
              {sigText}
            </div>
          )}
        </div>

        {/* Validation error */}
        {sigError && (
          <div
            className="mb-4 rounded-sm border px-4 py-3 text-sm"
            style={{
              backgroundColor: 'rgba(255,59,59,0.08)',
              borderColor: 'rgba(255,59,59,0.3)',
              color: '#ff6b6b',
            }}
          >
            {sigError}
          </div>
        )}

        {/* Actions */}
        <div
          className="flex items-center justify-between pt-4 border-t"
          style={{ borderColor: 'rgba(255,255,255,0.06)' }}
        >
          <button
            type="button"
            onClick={() => router.push('/signup')}
            disabled={signing}
            className="text-sm transition-colors disabled:opacity-40"
            style={{ color: 'rgba(255,255,255,0.4)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.8)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.4)')}
          >
            ← Back
          </button>
          <button
            type="submit"
            disabled={signing}
            className="bg-[#ff6b1a] text-black font-bold px-6 py-2.5 text-sm uppercase tracking-wider hover:bg-[#ff8c42] transition-colors rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {signing ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Signing…
              </span>
            ) : (
              'Sign & Continue →'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
