'use client';

import React, { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

const AGENCY_TYPES = ['EMS', 'Fire EMS', 'Fire Dept', 'Transport'];

const ESTIMATED_UNITS = ['1-5', '6-15', '16-30', '30+'];

const US_STATES = [
  'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut',
  'Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa',
  'Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan',
  'Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada',
  'New Hampshire','New Jersey','New Mexico','New York','North Carolina',
  'North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island',
  'South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont',
  'Virginia','Washington','West Virginia','Wisconsin','Wyoming',
];

interface FormData {
  agency_name: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  agency_type: string;
  state: string;
  estimated_units: string;
  referral_source: string;
}

interface FieldErrors {
  agency_name?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  agency_type?: string;
  state?: string;
  estimated_units?: string;
}

const inputClass =
  'bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm text-white placeholder-[rgba(255,255,255,0.3)] focus:outline-none focus:border-[#ff6b1a] rounded-sm w-full';

const selectClass =
  'bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] px-3 py-2 text-sm text-white focus:outline-none focus:border-[#ff6b1a] rounded-sm w-full appearance-none';

function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return (
    <p className="mt-1 text-xs" style={{ color: '#ff6b6b' }}>
      {msg}
    </p>
  );
}

function Label({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label
      className="block text-xs font-semibold mb-1.5 uppercase tracking-wider"
      style={{ color: 'rgba(255,255,255,0.55)' }}
    >
      {children}
      {required && <span style={{ color: '#ff6b1a' }}> *</span>}
    </label>
  );
}

export default function SignupPage() {
  const router = useRouter();

  const [form, setForm] = useState<FormData>({
    agency_name: '',
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    agency_type: '',
    state: '',
    estimated_units: '',
    referral_source: '',
  });

  const [errors, setErrors]     = useState<FieldErrors>({});
  const [apiError, setApiError] = useState('');
  const [loading, setLoading]   = useState(false);

  const set = useCallback(
    (field: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setForm(prev => ({ ...prev, [field]: e.target.value }));
      setErrors(prev => ({ ...prev, [field]: undefined }));
    },
    []
  );

  const validate = (): boolean => {
    const e: FieldErrors = {};
    if (!form.agency_name.trim())    e.agency_name    = 'Agency name is required.';
    if (!form.first_name.trim())     e.first_name     = 'First name is required.';
    if (!form.last_name.trim())      e.last_name      = 'Last name is required.';
    if (!form.email.trim())          e.email          = 'Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
                                     e.email          = 'Enter a valid email address.';
    if (!form.phone.trim())          e.phone          = 'Phone number is required.';
    if (!form.agency_type)           e.agency_type    = 'Select an agency type.';
    if (!form.state)                 e.state          = 'Select a state.';
    if (!form.estimated_units)       e.estimated_units = 'Select estimated units.';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setApiError('');
      if (!validate()) return;
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/public/onboarding/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agency_name:     form.agency_name.trim(),
            first_name:      form.first_name.trim(),
            last_name:       form.last_name.trim(),
            email:           form.email.trim(),
            phone:           form.phone.trim(),
            agency_type:     form.agency_type,
            state:           form.state,
            estimated_units: form.estimated_units,
            referral_source: form.referral_source.trim() || undefined,
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
        const appId = data?.application_id || data?.id || '';
        if (!appId) throw new Error('No application ID returned from server.');

        localStorage.setItem('qs_app_id',        appId);
        localStorage.setItem('qs_signer_email',  form.email.trim());
        localStorage.setItem('qs_signer_name',   `${form.first_name.trim()} ${form.last_name.trim()}`);
        localStorage.setItem('qs_agency_name',   form.agency_name.trim());

        router.push('/signup/legal');
      } catch (err: unknown) {
        setApiError(err instanceof Error ? err.message : 'An unexpected error occurred.');
      } finally {
        setLoading(false);
      }
    },
    [form, router]
  );

  return (
    <div
      className="rounded-sm border p-6 md:p-8"
      style={{
        backgroundColor: '#0b0f14',
        borderColor: 'rgba(255,255,255,0.08)',
      }}
    >
      {/* Header */}
      <div className="mb-6 border-b pb-5" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <h1
          className="text-xl font-bold uppercase tracking-wider text-white"
          style={{ fontFamily: "'Barlow Condensed', 'Barlow', sans-serif" }}
        >
          Agency Information
        </h1>
        <p className="mt-1 text-sm" style={{ color: 'rgba(255,255,255,0.45)' }}>
          Tell us about your agency to get started with FusionEMS Quantum.
        </p>
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

      <form onSubmit={handleSubmit} noValidate>
        {/* Agency Name — full width */}
        <div className="mb-4">
          <Label required>Agency Name</Label>
          <input
            type="text"
            className={inputClass}
            placeholder="e.g. Riverside EMS District"
            value={form.agency_name}
            onChange={set('agency_name')}
            disabled={loading}
          />
          <FieldError msg={errors.agency_name} />
        </div>

        {/* First / Last name */}
        <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label required>First Name</Label>
            <input
              type="text"
              className={inputClass}
              placeholder="John"
              value={form.first_name}
              onChange={set('first_name')}
              disabled={loading}
            />
            <FieldError msg={errors.first_name} />
          </div>
          <div>
            <Label required>Last Name</Label>
            <input
              type="text"
              className={inputClass}
              placeholder="Smith"
              value={form.last_name}
              onChange={set('last_name')}
              disabled={loading}
            />
            <FieldError msg={errors.last_name} />
          </div>
        </div>

        {/* Email / Phone */}
        <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label required>Email</Label>
            <input
              type="email"
              className={inputClass}
              placeholder="you@agency.org"
              value={form.email}
              onChange={set('email')}
              disabled={loading}
            />
            <FieldError msg={errors.email} />
          </div>
          <div>
            <Label required>Phone</Label>
            <input
              type="tel"
              className={inputClass}
              placeholder="(555) 000-0000"
              value={form.phone}
              onChange={set('phone')}
              disabled={loading}
            />
            <FieldError msg={errors.phone} />
          </div>
        </div>

        {/* Agency Type / State */}
        <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label required>Agency Type</Label>
            <div className="relative">
              <select
                className={selectClass}
                value={form.agency_type}
                onChange={set('agency_type')}
                disabled={loading}
              >
                <option value="" disabled>Select type…</option>
                {AGENCY_TYPES.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <div
                className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2"
                style={{ color: 'rgba(255,255,255,0.35)' }}
              >
                ▾
              </div>
            </div>
            <FieldError msg={errors.agency_type} />
          </div>
          <div>
            <Label required>State</Label>
            <div className="relative">
              <select
                className={selectClass}
                value={form.state}
                onChange={set('state')}
                disabled={loading}
              >
                <option value="" disabled>Select state…</option>
                {US_STATES.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <div
                className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2"
                style={{ color: 'rgba(255,255,255,0.35)' }}
              >
                ▾
              </div>
            </div>
            <FieldError msg={errors.state} />
          </div>
        </div>

        {/* Estimated Units */}
        <div className="mb-4">
          <Label required>Estimated Units</Label>
          <div className="flex flex-wrap gap-2 mt-1">
            {ESTIMATED_UNITS.map(u => {
              const selected = form.estimated_units === u;
              return (
                <button
                  key={u}
                  type="button"
                  onClick={() => {
                    setForm(prev => ({ ...prev, estimated_units: u }));
                    setErrors(prev => ({ ...prev, estimated_units: undefined }));
                  }}
                  disabled={loading}
                  className="px-4 py-2 text-sm font-semibold rounded-sm transition-colors"
                  style={{
                    backgroundColor: selected ? 'rgba(255,107,26,0.15)' : 'rgba(255,255,255,0.04)',
                    border: selected
                      ? '1px solid #ff6b1a'
                      : '1px solid rgba(255,255,255,0.1)',
                    color: selected ? '#ff6b1a' : 'rgba(255,255,255,0.55)',
                  }}
                >
                  {u}
                </button>
              );
            })}
          </div>
          <FieldError msg={errors.estimated_units} />
        </div>

        {/* Referral source */}
        <div className="mb-7">
          <Label>How did you hear about us?</Label>
          <input
            type="text"
            className={inputClass}
            placeholder="Conference, colleague, web search… (optional)"
            value={form.referral_source}
            onChange={set('referral_source')}
            disabled={loading}
          />
        </div>

        {/* Submit */}
        <div className="flex items-center justify-between pt-2 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
            Fields marked <span style={{ color: '#ff6b1a' }}>*</span> are required
          </p>
          <button
            type="submit"
            disabled={loading}
            className="bg-[#ff6b1a] text-black font-bold px-6 py-2.5 text-sm uppercase tracking-wider hover:bg-[#ff8c42] transition-colors rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Processing…
              </span>
            ) : (
              'Continue to Legal →'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
