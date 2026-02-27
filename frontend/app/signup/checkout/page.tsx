'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export default function CheckoutPage() {
  const router = useRouter();

  const [status,       setStatus]       = useState<'loading' | 'redirecting' | 'fallback' | 'error'>('loading');
  const [checkoutUrl,  setCheckoutUrl]  = useState('');
  const [errorMsg,     setErrorMsg]     = useState('');
  const [agencyName,   setAgencyName]   = useState('');

  useEffect(() => {
    const applicationId = localStorage.getItem('qs_app_id') || '';
    const storedAgency  = localStorage.getItem('qs_agency_name') || '';
    setAgencyName(storedAgency);

    if (!applicationId) {
      setErrorMsg('No application ID found. Please restart the signup process.');
      setStatus('error');
      return;
    }

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/public/onboarding/checkout/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ application_id: applicationId }),
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
        const url  = data?.checkout_url || '';
        if (!url) throw new Error('No checkout URL returned from server.');

        setCheckoutUrl(url);
        setStatus('redirecting');

        // Brief delay to show "redirecting" state, then navigate
        setTimeout(() => {
          try {
            window.location.href = url;
            // If we're still here after 2s, show fallback
            setTimeout(() => setStatus('fallback'), 2000);
          } catch {
            setStatus('fallback');
          }
        }, 1200);
      } catch (err: unknown) {
        setErrorMsg(err instanceof Error ? err.message : 'Failed to start checkout session.');
        setStatus('error');
      }
    })();
  }, []);

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
          Checkout
        </h1>
        <p className="mt-1 text-sm" style={{ color: 'rgba(255,255,255,0.45)' }}>
          Secure payment processing via Stripe.
        </p>
      </div>

      {/* Plan Summary Card */}
      <div
        className="rounded-sm border mb-7 overflow-hidden"
        style={{ borderColor: 'rgba(255,255,255,0.08)' }}
      >
        {/* Card header */}
        <div
          className="px-5 py-3 border-b"
          style={{
            backgroundColor: 'rgba(255,107,26,0.08)',
            borderColor: 'rgba(255,107,26,0.2)',
          }}
        >
          <span
            className="text-xs font-bold uppercase tracking-wider"
            style={{ color: '#ff6b1a' }}
          >
            Order Summary
          </span>
        </div>

        {/* Plan row */}
        <div
          className="px-5 py-4 flex items-center justify-between"
          style={{ backgroundColor: 'rgba(255,255,255,0.02)' }}
        >
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              {/* Hex icon */}
              <svg width="18" height="18" viewBox="0 0 36 36" fill="none">
                <polygon points="18,2 33,10 33,26 18,34 3,26 3,10" fill="#ff6b1a" />
                <text x="18" y="23" textAnchor="middle" fill="black" fontSize="11" fontWeight="900" fontFamily="'Barlow Condensed', sans-serif">FQ</text>
              </svg>
              <span className="text-sm font-bold text-white tracking-wide">
                FusionEMS Quantum
              </span>
            </div>
            <p className="text-xs mt-0.5 ml-6" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Full Platform — All Modules Included
            </p>
            {agencyName && (
              <p className="text-xs mt-0.5 ml-6" style={{ color: 'rgba(255,255,255,0.3)' }}>
                Agency: {agencyName}
              </p>
            )}
          </div>
          <div className="text-right">
            <div
              className="text-sm font-bold"
              style={{ color: 'rgba(255,255,255,0.55)' }}
            >
              Contact for pricing
            </div>
            <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.25)' }}>
              Custom quote
            </div>
          </div>
        </div>

        {/* Included features */}
        <div
          className="px-5 py-3 border-t"
          style={{ borderColor: 'rgba(255,255,255,0.06)', backgroundColor: 'rgba(255,255,255,0.015)' }}
        >
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            {[
              'ePCR & Dispatch',
              'Billing & RCM',
              'NEMSIS Compliance',
              'Voice/SMS/Fax',
              'Fleet Management',
              'Analytics Dashboard',
              'HIPAA-Compliant Storage',
              'API Access',
            ].map(feature => (
              <div key={feature} className="flex items-center gap-1.5">
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="#4caf50" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span className="text-xs" style={{ color: 'rgba(255,255,255,0.5)' }}>{feature}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* State machine content */}
      {status === 'loading' && (
        <div className="flex flex-col items-center justify-center py-10 gap-4">
          <svg className="animate-spin h-10 w-10" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-20" cx="12" cy="12" r="10" stroke="#ff6b1a" strokeWidth="3" />
            <path className="opacity-80" fill="#ff6b1a" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.45)' }}>
            Preparing your checkout session…
          </p>
        </div>
      )}

      {status === 'redirecting' && (
        <div className="flex flex-col items-center justify-center py-10 gap-4">
          <div className="flex items-center gap-3">
            <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-20" cx="12" cy="12" r="10" stroke="#22d3ee" strokeWidth="3" />
              <path className="opacity-80" fill="#22d3ee" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            <p className="text-sm font-semibold" style={{ color: '#22d3ee' }}>
              Redirecting to Stripe Checkout…
            </p>
          </div>
          <p className="text-xs text-center" style={{ color: 'rgba(255,255,255,0.3)' }}>
            You will be redirected to Stripe&apos;s secure checkout page momentarily.
          </p>
        </div>
      )}

      {status === 'fallback' && (
        <div className="flex flex-col items-center gap-4 py-6">
          <div
            className="rounded-sm border px-4 py-3 text-sm w-full"
            style={{
              backgroundColor: 'rgba(34,211,238,0.06)',
              borderColor: 'rgba(34,211,238,0.2)',
              color: 'rgba(255,255,255,0.65)',
            }}
          >
            <p className="font-semibold mb-1" style={{ color: '#22d3ee' }}>
              Redirect did not complete automatically.
            </p>
            <p className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Click the button below to continue to Stripe Checkout.
            </p>
          </div>
          <a
            href={checkoutUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-[#ff6b1a] text-black font-bold px-6 py-2.5 text-sm uppercase tracking-wider hover:bg-[#ff8c42] transition-colors rounded-sm inline-block"
          >
            Continue to Stripe Checkout →
          </a>
          <p
            className="text-xs break-all text-center"
            style={{ color: 'rgba(255,255,255,0.2)' }}
          >
            {checkoutUrl}
          </p>
        </div>
      )}

      {status === 'error' && (
        <div className="space-y-4">
          <div
            className="rounded-sm border px-4 py-3 text-sm"
            style={{
              backgroundColor: 'rgba(255,59,59,0.08)',
              borderColor: 'rgba(255,59,59,0.3)',
              color: '#ff6b6b',
            }}
          >
            <span className="font-semibold">Error: </span>{errorMsg}
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => router.push('/signup/legal')}
              className="text-sm transition-colors"
              style={{ color: 'rgba(255,255,255,0.4)' }}
              onMouseEnter={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.8)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.4)')}
            >
              ← Back to Legal
            </button>
            <button
              onClick={() => window.location.reload()}
              className="bg-[#ff6b1a] text-black font-bold px-4 py-2 text-sm uppercase tracking-wider hover:bg-[#ff8c42] transition-colors rounded-sm"
            >
              Retry
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
