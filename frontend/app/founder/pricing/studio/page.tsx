'use client';

import React, { useState } from 'react';

type StudioTab = 'catalog' | 'pricebooks' | 'estimator';

const TABS: { id: StudioTab; label: string }[] = [
  { id: 'catalog', label: 'Product Catalog' },
  { id: 'pricebooks', label: 'Pricebooks' },
  { id: 'estimator', label: 'Price Estimator' },
];

interface PriceEntry {
  tier: string;
  monthly: number;
  perTransport?: number;
  description: string;
}

const CATALOG: { product: string; key: string; color: string; prices: PriceEntry[] }[] = [
  {
    product: 'Scheduling Only',
    key: 'SCHEDULING_ONLY',
    color: 'var(--color-system-billing)',
    prices: [
      { tier: 'S1 — Starter', monthly: 199, description: 'Up to 10 crew, basic scheduling' },
      { tier: 'S2 — Growth', monthly: 399, description: 'Up to 30 crew, swap/trade/timeoff' },
      { tier: 'S3 — Scale', monthly: 699, description: 'Unlimited crew, AI draft, coverage engine' },
    ],
  },
  {
    product: 'Billing Automation',
    key: 'BILLING_AUTOMATION_BASE',
    color: 'var(--q-orange)',
    prices: [
      { tier: 'B1 — Essentials', monthly: 399, perTransport: 6.00, description: '< 100 transports/mo' },
      { tier: 'B2 — Standard', monthly: 599, perTransport: 5.00, description: '100–300 transports/mo' },
      { tier: 'B3 — Pro', monthly: 999, perTransport: 4.00, description: '300–600 transports/mo' },
      { tier: 'B4 — Enterprise', monthly: 1499, perTransport: 3.25, description: '600+ transports/mo' },
    ],
  },
  {
    product: 'CCT Transport Ops',
    key: 'CCT_TRANSPORT_OPS_ADDON',
    color: '#a855f7',
    prices: [
      { tier: 'CCT Add-on', monthly: 399, description: 'Critical care transport dispatch + ePCR fields' },
    ],
  },
  {
    product: 'HEMS Module',
    key: 'HEMS_ADDON',
    color: 'var(--q-yellow)',
    prices: [
      { tier: 'HEMS Add-on', monthly: 750, description: 'Helicopter/fixed-wing pilot portal + acceptance checklist + risk audit' },
    ],
  },
  {
    product: 'TRIP Pack (WI)',
    key: 'TRIP_PACK_ADDON',
    color: 'var(--q-green)',
    prices: [
      { tier: 'TRIP Add-on', monthly: 199, description: 'Wisconsin Tax Refund Intercept — government agencies only' },
    ],
  },
];

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm px-4 py-3">
      <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-1">{label}</div>
      <div className="text-lg font-bold text-text-primary">{value}</div>
      {sub && <div className="text-[10px] text-[rgba(255,255,255,0.35)] mt-0.5">{sub}</div>}
    </div>
  );
}

function CatalogTab() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Active Products" value="8" />
        <StatCard label="Active Prices" value="10" />
        <StatCard label="Active Pricebook" value="v1.0" sub="published" />
        <StatCard label="Stripe Sync" value="Live" sub="SSM-backed" />
      </div>

      {CATALOG.map((product) => (
        <div key={product.key} className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle">
            <div className="flex items-center gap-3">
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: product.color }} />
              <span className="text-sm font-semibold text-text-primary">{product.product}</span>
              <span className="text-[10px] text-[rgba(255,255,255,0.3)] font-mono">{product.key}</span>
            </div>
            <button className="h-6 px-2.5 bg-orange-ghost border border-[rgba(255,107,26,0.2)] text-[10px] font-semibold uppercase tracking-wider text-orange hover:bg-[rgba(255,107,26,0.14)] transition-colors rounded-sm">
              Edit
            </button>
          </div>
          <div className="divide-y divide-[rgba(255,255,255,0.04)]">
            {product.prices.map((price) => (
              <div key={price.tier} className="flex items-center justify-between px-4 py-3">
                <div>
                  <div className="text-xs font-medium text-text-primary">{price.tier}</div>
                  <div className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">{price.description}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold" style={{ color: product.color }}>
                    ${price.monthly.toLocaleString()}<span className="text-[10px] font-normal text-[rgba(255,255,255,0.35)]">/mo</span>
                  </div>
                  {price.perTransport && (
                    <div className="text-[10px] text-[rgba(255,255,255,0.4)]">+ ${price.perTransport.toFixed(2)}/transport</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function PricebooksTab() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs text-[rgba(255,255,255,0.5)]">Versioned pricebooks — draft → scheduled → active → archived</div>
        <button className="h-7 px-3 bg-[rgba(255,107,26,0.1)] border border-[rgba(255,107,26,0.25)] text-[10px] font-semibold uppercase tracking-wider text-orange hover:bg-[rgba(255,107,26,0.18)] transition-colors rounded-sm">
          New Draft
        </button>
      </div>

      <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">
          <span>Version</span><span>Label</span><span>Status</span><span>Effective Date</span><span>Created By</span><span>Actions</span>
        </div>
        <div className="px-4 py-3 grid grid-cols-6 items-center border-b border-border-subtle">
          <span className="text-xs font-mono text-text-primary">v1.0</span>
          <span className="text-xs text-[rgba(255,255,255,0.7)]">Initial Catalog</span>
          <span className="inline-flex items-center px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-sm bg-[rgba(76,175,80,0.12)] text-status-active w-fit">Active</span>
          <span className="text-xs text-[rgba(255,255,255,0.5)]">2026-01-01</span>
          <span className="text-xs text-[rgba(255,255,255,0.5)]">System</span>
          <div className="flex gap-2">
            <button className="h-6 px-2.5 bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-[10px] text-[rgba(255,255,255,0.5)] hover:text-text-primary transition-colors rounded-sm">View</button>
            <button className="h-6 px-2.5 bg-[rgba(255,255,255,0.04)] border border-border-DEFAULT text-[10px] text-[rgba(255,255,255,0.5)] hover:text-text-primary transition-colors rounded-sm">Clone</button>
          </div>
        </div>
        <div className="px-4 py-8 text-center text-xs text-[rgba(255,255,255,0.25)]">Draft a new pricebook to test pricing changes before activating</div>
      </div>
    </div>
  );
}

function EstimatorTab() {
  const [plan, setPlan] = useState('SCHEDULING_ONLY');
  const [tier, setTier] = useState('S1');
  const [transports, setTransports] = useState(150);
  const [addons, setAddons] = useState<string[]>([]);

  const toggleAddon = (key: string) => {
    setAddons((prev) => prev.includes(key) ? prev.filter((a) => a !== key) : [...prev, key]);
  };

  const baseMonthly =
    plan === 'SCHEDULING_ONLY'
      ? (tier === 'S1' ? 199 : tier === 'S2' ? 399 : 699)
      : plan === 'BILLING_AUTOMATION_BASE'
      ? (tier === 'B1' ? 399 : tier === 'B2' ? 599 : tier === 'B3' ? 999 : 1499)
      : 0;

  const perTransportRate =
    plan === 'BILLING_AUTOMATION_BASE'
      ? (tier === 'B1' ? 6 : tier === 'B2' ? 5 : tier === 'B3' ? 4 : 3.25)
      : 0;

  const addonPrices: Record<string, number> = { CCT: 399, HEMS: 750, TRIP: 199 };
  const addonLabels: Record<string, string> = { CCT: 'CCT Add-on', HEMS: 'HEMS Add-on', TRIP: 'TRIP Pack' };
  const addonTotal = addons.reduce((sum, a) => sum + (addonPrices[a] ?? 0), 0);
  const total = baseMonthly + perTransportRate * transports + addonTotal;

  return (
    <div className="grid grid-cols-2 gap-6">
      <div className="space-y-4">
        <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm p-4">
          <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-3">Base Plan</div>
          <div className="flex gap-2 mb-3">
            {['SCHEDULING_ONLY', 'BILLING_AUTOMATION_BASE'].map((p) => (
              <button
                key={p}
                onClick={() => { setPlan(p); setTier(p === 'SCHEDULING_ONLY' ? 'S1' : 'B1'); }}
                className={`flex-1 h-8 text-[11px] font-medium rounded-sm border transition-colors ${
                  plan === p
                    ? 'bg-[rgba(255,107,26,0.15)] border-[rgba(255,107,26,0.4)] text-orange'
                    : 'bg-[rgba(255,255,255,0.03)] border-border-DEFAULT text-[rgba(255,255,255,0.5)] hover:text-text-primary'
                }`}
              >
                {p === 'SCHEDULING_ONLY' ? 'Scheduling' : 'Billing Auto'}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            {(plan === 'SCHEDULING_ONLY' ? ['S1', 'S2', 'S3'] : ['B1', 'B2', 'B3', 'B4']).map((t) => (
              <button
                key={t}
                onClick={() => setTier(t)}
                className={`flex-1 h-7 text-[11px] font-mono rounded-sm border transition-colors ${
                  tier === t
                    ? 'bg-[rgba(34,211,238,0.12)] border-[rgba(34,211,238,0.3)] text-system-billing'
                    : 'bg-[rgba(255,255,255,0.03)] border-border-DEFAULT text-[rgba(255,255,255,0.45)] hover:text-text-primary'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {plan === 'BILLING_AUTOMATION_BASE' && (
          <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)]">Monthly Transports</div>
              <span className="text-sm font-bold text-text-primary">{transports}</span>
            </div>
            <input
              type="range"
              min={10}
              max={1000}
              step={10}
              value={transports}
              onChange={(e) => setTransports(Number(e.target.value))}
              className="w-full accent-[#ff6b1a]"
            />
            <div className="flex justify-between text-[10px] text-[rgba(255,255,255,0.3)] mt-1">
              <span>10</span><span>500</span><span>1000</span>
            </div>
          </div>
        )}

        <div className="bg-bg-base border border-[rgba(255,255,255,0.07)] rounded-sm p-4">
          <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-3">Add-ons</div>
          {[
            { key: 'CCT', label: 'CCT Transport Ops', price: 399 },
            { key: 'HEMS', label: 'HEMS Module', price: 750 },
            { key: 'TRIP', label: 'TRIP Pack (WI Gov)', price: 199 },
          ].map((addon) => (
            <label key={addon.key} className="flex items-center justify-between py-2 border-b border-border-subtle last:border-0 cursor-pointer">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={addons.includes(addon.key)}
                  onChange={() => toggleAddon(addon.key)}
                  className="accent-[#ff6b1a]"
                />
                <span className="text-xs text-[rgba(255,255,255,0.7)]">{addon.label}</span>
              </div>
              <span className="text-xs text-[rgba(255,255,255,0.5)]">+${addon.price}/mo</span>
            </label>
          ))}
        </div>
      </div>

      <div className="bg-bg-base border border-[rgba(255,107,26,0.2)] rounded-sm p-5 flex flex-col">
        <div className="text-[10px] uppercase tracking-widest text-orange-dim mb-4">Monthly Estimate</div>
        <div className="space-y-3 flex-1">
          <div className="flex justify-between text-xs">
            <span className="text-[rgba(255,255,255,0.5)]">
              Base ({plan === 'SCHEDULING_ONLY' ? `Scheduling ${tier}` : `Billing Auto ${tier}`})
            </span>
            <span className="text-text-primary font-medium">${baseMonthly.toLocaleString()}</span>
          </div>
          {perTransportRate > 0 && (
            <div className="flex justify-between text-xs">
              <span className="text-[rgba(255,255,255,0.5)]">Usage ({transports} × ${perTransportRate.toFixed(2)})</span>
              <span className="text-text-primary font-medium">${(perTransportRate * transports).toFixed(2)}</span>
            </div>
          )}
          {addons.map((a) => (
            <div key={a} className="flex justify-between text-xs">
              <span className="text-[rgba(255,255,255,0.5)]">{addonLabels[a]}</span>
              <span className="text-text-primary font-medium">${addonPrices[a].toLocaleString()}</span>
            </div>
          ))}
        </div>
        <div className="border-t border-border-DEFAULT pt-4 mt-4">
          <div className="flex justify-between items-end">
            <span className="text-xs text-[rgba(255,255,255,0.5)]">Total / month</span>
            <span className="text-2xl font-black text-orange">
              ${total.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="text-[10px] text-[rgba(255,255,255,0.3)] mt-1">
            Annual: ${(total * 12).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PricingStudioPage() {
  const [activeTab, setActiveTab] = useState<StudioTab>('catalog');

  const content: Record<StudioTab, React.ReactNode> = {
    catalog: <CatalogTab />,
    pricebooks: <PricebooksTab />,
    estimator: <EstimatorTab />,
  };

  return (
    <div className="p-6 max-w-[1300px]">
      <div className="mb-6">
        <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.3)] mb-1">Founder OS</div>
        <h1 className="text-xl font-bold text-text-primary">Pricing Studio</h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Product catalog, versioned pricebooks, price estimator, and Stripe catalog management</p>
      </div>

      <div className="flex gap-0 mb-6 border-b border-border-DEFAULT">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative px-4 py-2.5 text-xs font-medium transition-colors ${
              activeTab === tab.id ? 'text-text-primary' : 'text-[rgba(255,255,255,0.4)] hover:text-[rgba(255,255,255,0.7)]'
            }`}
          >
            {tab.label}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-orange" />
            )}
          </button>
        ))}
      </div>

      <div>{content[activeTab]}</div>
    </div>
  );
}
