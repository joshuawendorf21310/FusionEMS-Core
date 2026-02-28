'use client';

import React, { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

const PLANS = [
  { code: 'SCHEDULING_ONLY', label: 'Scheduling Only', desc: 'Calendar, shifts, crew, bids, scheduling PWA', price: 'from $199/mo', color: 'var(--color-status-info)' },
  { code: 'OPS_CORE', label: 'Ops Core', desc: 'TransportLink + CAD + CrewLink + Scheduling', price: 'Contact us', color: 'var(--q-green)' },
  { code: 'CLINICAL_CORE', label: 'Clinical Core', desc: 'ePCR + NEMSIS/WI validation + Scheduling', price: 'Contact us', color: '#a855f7' },
  { code: 'FULL_STACK', label: 'Full Stack', desc: 'Everything — Ops + Clinical + HEMS + NERIS', price: 'Contact us', color: 'var(--q-orange)' },
];

const SCHEDULING_TIERS = [
  { code: 'S1', label: '1–25 active users', price: '$199/mo' },
  { code: 'S2', label: '26–75 active users', price: '$399/mo' },
  { code: 'S3', label: '76–150 active users', price: '$699/mo' },
];

const BILLING_TIERS = [
  { code: 'B1', label: '0–150 claims/mo', base: '$399/mo', per_claim: '+$6/claim' },
  { code: 'B2', label: '151–400 claims/mo', base: '$599/mo', per_claim: '+$5/claim' },
  { code: 'B3', label: '401–1,000 claims/mo', base: '$999/mo', per_claim: '+$4/claim' },
  { code: 'B4', label: '1,001+ claims/mo', base: '$1,499/mo', per_claim: '+$3.25/claim' },
];

const ADDONS = [
  { code: 'CCT_TRANSPORT_OPS', label: 'CCT / Transport Ops', price: '+$399/mo', gov_only: false },
  { code: 'HEMS_OPS', label: 'HEMS Ops (rotor + fixed-wing)', price: '+$750/mo', gov_only: false },
  { code: 'BILLING_AUTOMATION', label: 'Billing Automation', price: 'from $399/mo + per claim', gov_only: false },
  { code: 'TRIP_PACK', label: 'Wisconsin TRIP Pack (gov agencies only)', price: '+$199/mo', gov_only: true },
];

const COLLECTIONS_MODES = [
  { code: 'none', label: 'No soft collections' },
  { code: 'soft_only', label: 'Soft collections (statements + payment portal)' },
  { code: 'soft_and_handoff', label: 'Soft + vendor handoff export' },
];

const US_STATES = ['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming'];
const AGENCY_TYPES = ['EMS', 'Fire EMS', 'Fire Dept', 'Air Medical', 'Transport'];

const inputCls = 'bg-[rgba(255,255,255,0.05)] border border-border-DEFAULT px-3 py-2 text-sm text-text-primary placeholder-[rgba(255,255,255,0.3)] focus:outline-none focus:border-orange rounded-sm w-full';
const selectCls = 'bg-[rgba(255,255,255,0.05)] border border-border-DEFAULT px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-orange rounded-sm w-full appearance-none';
const labelCls = 'block text-xs font-semibold mb-1.5 uppercase tracking-wider text-[rgba(255,255,255,0.55)]';

type Step = 1 | 2 | 3 | 4 | 5;

export default function SignupPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [plan, setPlan] = useState('');
  const [tier, setTier] = useState('');
  const [billingTier, setBillingTier] = useState('');
  const [addons, setAddons] = useState<string[]>([]);
  const [isGovEntity, setIsGovEntity] = useState(false);
  const [collectionsMode, setCollectionsMode] = useState('none');
  const [statementChannels, setStatementChannels] = useState<string[]>(['mail']);
  const [collectorVendor, setCollectorVendor] = useState('');
  const [placementMethod, setPlacementMethod] = useState('portal_upload');

  const [agencyName, setAgencyName] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [agencyType, setAgencyType] = useState('');
  const [state, setState] = useState('Wisconsin');

  const toggleAddon = (code: string) => {
    setAddons(prev => prev.includes(code) ? prev.filter(a => a !== code) : [...prev, code]);
  };

  const toggleChannel = (ch: string) => {
    setStatementChannels(prev => prev.includes(ch) ? prev.filter(c => c !== ch) : [...prev, ch]);
  };

  const canProceed1 = !!plan && (plan !== 'SCHEDULING_ONLY' || !!tier);
  const canProceed4 = agencyName && firstName && lastName && email && agencyType && state;

  async function submit() {
    setLoading(true); setError('');
    try {
      const payload = {
        agency_name: agencyName, first_name: firstName, last_name: lastName,
        email, phone, agency_type: agencyType, state,
        plan_code: plan, tier_code: tier || billingTier,
        modules: addons,
        is_government_entity: isGovEntity,
        collections_mode: collectionsMode,
        trip_enabled: addons.includes('TRIP_PACK') && isGovEntity,
        statement_channels: statementChannels,
        collector_vendor_name: collectorVendor,
        placement_method: placementMethod,
      };
      const res = await fetch(`${API_BASE}/public/onboarding/apply`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b?.detail || `Error ${res.status}`); }
      const data = await res.json();
      localStorage.setItem('qs_app_id', data.id || data.application_id || '');
      localStorage.setItem('qs_agency_name', agencyName);
      router.push('/signup/legal');
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen bg-bg-void text-text-primary flex flex-col items-center py-12 px-4">
      <div className="w-full max-w-3xl">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-9 h-9 bg-orange flex items-center justify-center text-sm font-black text-text-inverse" style={{ clipPath: 'polygon(0 0, calc(100% - 7px) 0, 100% 7px, 100% 100%, 0 100%)' }}>FQ</div>
          <div>
            <div className="text-lg font-bold tracking-wide">QuantumEMS</div>
            <div className="text-xs text-[rgba(255,255,255,0.4)]">Agency Signup</div>
          </div>
        </div>

        <div className="flex gap-2 mb-10">
          {(['Plan','Addons','Collections','Agency Info','Review'] as const).map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step === i+1 ? 'bg-orange text-text-inverse' : step > i+1 ? 'bg-status-active text-text-inverse' : 'bg-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.4)]'}`}>{i+1}</div>
              <span className={`text-xs hidden sm:block ${step === i+1 ? 'text-text-primary font-semibold' : 'text-[rgba(255,255,255,0.35)]'}`}>{label}</span>
              {i < 4 && <span className="text-[rgba(255,255,255,0.15)] text-xs">›</span>}
            </div>
          ))}
        </div>

        {step === 1 && (
          <div>
            <h2 className="text-xl font-bold mb-1">Choose your plan</h2>
            <p className="text-sm text-[rgba(255,255,255,0.45)] mb-6">One plan. Add what you need.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
              {PLANS.map(p => (
                <button key={p.code} onClick={() => { setPlan(p.code); setTier(''); }}
                  className={`text-left p-4 rounded-sm border transition-all ${plan === p.code ? 'border-orange bg-orange-ghost' : 'border-border-DEFAULT hover:border-[rgba(255,255,255,0.2)]'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
                    <span className="font-semibold text-sm">{p.label}</span>
                  </div>
                  <div className="text-xs text-[rgba(255,255,255,0.45)] mb-2">{p.desc}</div>
                  <div className="text-xs font-bold" style={{ color: p.color }}>{p.price}</div>
                </button>
              ))}
            </div>
            {plan === 'SCHEDULING_ONLY' && (
              <div className="mb-6">
                <div className={labelCls}>Select size tier</div>
                <div className="grid grid-cols-3 gap-2">
                  {SCHEDULING_TIERS.map(t => (
                    <button key={t.code} onClick={() => setTier(t.code)}
                      className={`p-3 rounded-sm border text-left transition-all ${tier === t.code ? 'border-orange bg-orange-ghost' : 'border-border-DEFAULT hover:border-[rgba(255,255,255,0.2)]'}`}>
                      <div className="text-xs font-semibold">{t.label}</div>
                      <div className="text-xs text-orange font-bold mt-1">{t.price}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="mb-4 flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={isGovEntity} onChange={e => setIsGovEntity(e.target.checked)} className="w-4 h-4 accent-[#ff6b1a]" />
                <span className="text-sm">We are a government agency (municipal/county/tribal)</span>
              </label>
            </div>
            <button disabled={!canProceed1} onClick={() => setStep(2)}
              className="w-full py-3 bg-orange text-text-inverse text-sm font-bold rounded-sm disabled:opacity-40 hover:bg-orange-bright transition-colors">
              Continue to Add-ons
            </button>
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 className="text-xl font-bold mb-1">Add-ons</h2>
            <p className="text-sm text-[rgba(255,255,255,0.45)] mb-6">Add capabilities to your plan.</p>
            <div className="space-y-2 mb-6">
              {ADDONS.filter(a => !a.gov_only || isGovEntity).map(a => (
                <label key={a.code} className={`flex items-center justify-between p-4 rounded-sm border cursor-pointer transition-all ${addons.includes(a.code) ? 'border-orange bg-orange-ghost' : 'border-border-DEFAULT hover:border-border-strong'}`}>
                  <div className="flex items-center gap-3">
                    <input type="checkbox" checked={addons.includes(a.code)} onChange={() => toggleAddon(a.code)} className="w-4 h-4 accent-[#ff6b1a]" />
                    <div>
                      <div className="text-sm font-semibold">{a.label}</div>
                      {a.gov_only && <div className="text-xs text-status-warning">Government agencies only</div>}
                    </div>
                  </div>
                  <div className="text-xs text-orange font-bold">{a.price}</div>
                </label>
              ))}
            </div>
            {addons.includes('BILLING_AUTOMATION') && (
              <div className="mb-6 p-4 border border-border-DEFAULT rounded-sm">
                <div className={labelCls}>Billing Automation tier</div>
                <div className="space-y-2">
                  {BILLING_TIERS.map(t => (
                    <label key={t.code} className={`flex items-center justify-between p-3 rounded-sm border cursor-pointer ${billingTier === t.code ? 'border-orange' : 'border-border-subtle'}`}>
                      <div className="flex items-center gap-2">
                        <input type="radio" checked={billingTier === t.code} onChange={() => setBillingTier(t.code)} className="accent-[#ff6b1a]" />
                        <span className="text-xs">{t.label}</span>
                      </div>
                      <span className="text-xs text-orange font-bold">{t.base} {t.per_claim}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
            <div className="flex gap-3">
              <button onClick={() => setStep(1)} className="flex-1 py-3 border border-border-strong text-sm font-bold rounded-sm hover:bg-[rgba(255,255,255,0.05)]">Back</button>
              <button onClick={() => setStep(3)} className="flex-1 py-3 bg-orange text-text-inverse text-sm font-bold rounded-sm hover:bg-orange-bright">Continue</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <h2 className="text-xl font-bold mb-1">Collections setup</h2>
            <p className="text-sm text-[rgba(255,255,255,0.45)] mb-6">How do you want to handle patient responsibility balances?</p>
            <div className="space-y-2 mb-6">
              {COLLECTIONS_MODES.map(m => (
                <label key={m.code} className={`flex items-center gap-3 p-4 rounded-sm border cursor-pointer transition-all ${collectionsMode === m.code ? 'border-orange bg-orange-ghost' : 'border-border-DEFAULT'}`}>
                  <input type="radio" checked={collectionsMode === m.code} onChange={() => setCollectionsMode(m.code)} className="accent-[#ff6b1a]" />
                  <span className="text-sm">{m.label}</span>
                </label>
              ))}
            </div>
            {collectionsMode !== 'none' && (
              <div className="mb-6 p-4 border border-border-DEFAULT rounded-sm space-y-4">
                <div>
                  <div className={labelCls}>Statement delivery channels</div>
                  <div className="flex gap-4">
                    {['mail','email','sms_link'].map(ch => (
                      <label key={ch} className="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" checked={statementChannels.includes(ch)} onChange={() => toggleChannel(ch)} className="accent-[#ff6b1a]" />
                        <span className="text-sm capitalize">{ch.replace('_', ' ')}</span>
                      </label>
                    ))}
                  </div>
                </div>
                {collectionsMode === 'soft_and_handoff' && (
                  <div className="space-y-3">
                    <div>
                      <label className={labelCls}>Collections vendor name (optional)</label>
                      <input value={collectorVendor} onChange={e => setCollectorVendor(e.target.value)} placeholder="e.g. ABC Collections Inc." className={inputCls} />
                    </div>
                    <div>
                      <label className={labelCls}>Placement method</label>
                      <select value={placementMethod} onChange={e => setPlacementMethod(e.target.value)} className={selectCls}>
                        <option value="portal_upload">Portal upload (download ZIP)</option>
                        <option value="sftp">SFTP (configure after signup)</option>
                        <option value="email">Email</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>
            )}
            <div className="flex gap-3">
              <button onClick={() => setStep(2)} className="flex-1 py-3 border border-border-strong text-sm font-bold rounded-sm hover:bg-[rgba(255,255,255,0.05)]">Back</button>
              <button onClick={() => setStep(4)} className="flex-1 py-3 bg-orange text-text-inverse text-sm font-bold rounded-sm hover:bg-orange-bright">Continue</button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div>
            <h2 className="text-xl font-bold mb-1">Agency information</h2>
            <p className="text-sm text-[rgba(255,255,255,0.45)] mb-6">Tell us about your organization.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              <div className="sm:col-span-2">
                <label className={labelCls}>Agency Name *</label>
                <input value={agencyName} onChange={e => setAgencyName(e.target.value)} placeholder="City of Example EMS" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>First Name *</label>
                <input value={firstName} onChange={e => setFirstName(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Last Name *</label>
                <input value={lastName} onChange={e => setLastName(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Email *</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Phone</label>
                <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Agency Type *</label>
                <select value={agencyType} onChange={e => setAgencyType(e.target.value)} className={selectCls}>
                  <option value="">Select...</option>
                  {AGENCY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>State *</label>
                <select value={state} onChange={e => setState(e.target.value)} className={selectCls}>
                  {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setStep(3)} className="flex-1 py-3 border border-border-strong text-sm font-bold rounded-sm hover:bg-[rgba(255,255,255,0.05)]">Back</button>
              <button disabled={!canProceed4} onClick={() => setStep(5)} className="flex-1 py-3 bg-orange text-text-inverse text-sm font-bold rounded-sm disabled:opacity-40 hover:bg-orange-bright">Review & Continue</button>
            </div>
          </div>
        )}

        {step === 5 && (
          <div>
            <h2 className="text-xl font-bold mb-1">Review your order</h2>
            <p className="text-sm text-[rgba(255,255,255,0.45)] mb-6">Confirm your selections before proceeding to legal signing and payment.</p>
            <div className="space-y-3 mb-6">
              {[
                { label: 'Plan', value: PLANS.find(p => p.code === plan)?.label || plan },
                { label: 'Tier', value: SCHEDULING_TIERS.find(t => t.code === tier)?.label || tier || '—' },
                { label: 'Add-ons', value: addons.length ? addons.join(', ') : 'None' },
                { label: 'Government entity', value: isGovEntity ? 'Yes' : 'No' },
                { label: 'Collections', value: COLLECTIONS_MODES.find(m => m.code === collectionsMode)?.label || collectionsMode },
                { label: 'Agency', value: `${agencyName} (${agencyType}, ${state})` },
                { label: 'Contact', value: `${firstName} ${lastName} · ${email}` },
              ].map(row => (
                <div key={row.label} className="flex justify-between py-2 border-b border-border-subtle text-sm">
                  <span className="text-[rgba(255,255,255,0.5)]">{row.label}</span>
                  <span className="font-semibold">{row.value}</span>
                </div>
              ))}
            </div>
            {error && <div className="mb-4 p-3 bg-[rgba(229,57,53,0.12)] border border-red-ghost text-red text-sm rounded-sm">{error}</div>}
            <div className="flex gap-3">
              <button onClick={() => setStep(4)} className="flex-1 py-3 border border-border-strong text-sm font-bold rounded-sm hover:bg-[rgba(255,255,255,0.05)]">Back</button>
              <button disabled={loading} onClick={submit} className="flex-1 py-3 bg-orange text-text-inverse text-sm font-bold rounded-sm disabled:opacity-50 hover:bg-orange-bright">
                {loading ? 'Submitting...' : 'Continue to Legal Signing'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
