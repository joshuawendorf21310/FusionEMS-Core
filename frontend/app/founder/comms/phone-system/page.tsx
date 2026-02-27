'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function PageHeader() {
  return (
    <div className="hud-rail pb-3 mb-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">
            CATEGORY 2 · MODULES C2.1–100
          </div>
          <h1 className="text-lg font-black uppercase tracking-wider text-white">AI Voice, Phone Tree, Ringing & Alerting System</h1>
          <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">
            100-item control surface — Natural Voice Engine · Visual Flow Builder · Escalation Ladder · Call Analytics · Alert Policies
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#22d3ee] animate-pulse" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#22d3ee]">AI VOICE LIVE</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function KpiStrip() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 mb-6">
      {[
        { label: 'Active Modules', value: '82', color: '#4caf50' },
        { label: 'Configured', value: '12', color: '#29b6f6' },
        { label: 'Pending', value: '6', color: '#ff9800' },
        { label: 'AI Resolution Rate', value: '79%', color: '#22d3ee' },
        { label: 'Avg Call Latency', value: '210ms', color: '#4caf50' },
        { label: 'Escalation Rate', value: '8.2%', color: '#a855f7' },
      ].map((item) => (
        <div
          key={item.label}
          className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-3"
          style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
        >
          <div className="text-[9px] uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-1">{item.label}</div>
          <div className="text-lg font-bold" style={{ color: item.color }}>{item.value}</div>
        </div>
      ))}
    </div>
  );
}

function CallQueueRow({ position, caller, intent, wait, score, aiCanResolve }: {
  position: number; caller: string; intent: string; wait: string; score: number; aiCanResolve: boolean;
}) {
  const scoreColor = score >= 80 ? '#e53935' : score >= 50 ? '#ff9800' : '#4caf50';
  return (
    <tr>
      <td className="py-2 pr-3 text-[10px] font-bold font-mono text-[rgba(255,107,26,0.6)]">{position}</td>
      <td className="py-2 pr-3 text-xs text-white">{caller}</td>
      <td className="py-2 pr-3">
        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 bg-[rgba(255,255,255,0.05)] text-[rgba(255,255,255,0.5)] rounded-sm">{intent}</span>
      </td>
      <td className="py-2 pr-3 text-xs text-[rgba(255,255,255,0.5)]">{wait}</td>
      <td className="py-2 pr-3">
        <div className="flex items-center gap-1.5">
          <div className="h-1 w-16 bg-[rgba(255,255,255,0.06)] rounded-full overflow-hidden">
            <div className="h-full rounded-full" style={{ width: `${score}%`, background: scoreColor }} />
          </div>
          <span className="text-[10px] font-semibold" style={{ color: scoreColor }}>{score}</span>
        </div>
      </td>
      <td className="py-2">
        <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-sm ${aiCanResolve ? 'text-[#4caf50] bg-[rgba(76,175,80,0.12)]' : 'text-[#ff9800] bg-[rgba(255,152,0,0.12)]'}`}>
          {aiCanResolve ? 'AI CAN RESOLVE' : 'ESCALATE'}
        </span>
      </td>
    </tr>
  );
}

function ScriptNode({ label, type, children, indent = 0 }: {
  label: string; type: 'trigger' | 'condition' | 'action' | 'escalate'; children?: string[]; indent?: number;
}) {
  const typeColor = { trigger: '#ff6b1a', condition: '#29b6f6', action: '#4caf50', escalate: '#e53935' }[type];
  const typeBg = { trigger: 'rgba(255,107,26,0.1)', condition: 'rgba(41,182,246,0.1)', action: 'rgba(76,175,80,0.1)', escalate: 'rgba(229,57,53,0.1)' }[type];
  return (
    <div style={{ marginLeft: indent * 16 }} className="mb-1">
      <div
        className="flex items-center gap-2 px-2 py-1.5 border-l-2 text-xs"
        style={{ borderLeftColor: typeColor, background: typeBg }}
      >
        <span className="text-[9px] font-bold uppercase tracking-wider w-16 flex-shrink-0" style={{ color: typeColor }}>{type}</span>
        <span className="text-[rgba(255,255,255,0.8)]">{label}</span>
      </div>
      {children && children.map((c, i) => (
        <ScriptNode key={i} label={c} type="action" indent={indent + 1} />
      ))}
    </div>
  );
}

function ModuleCard({
  number,
  title,
  desc,
  category,
  status,
  children,
}: {
  number: number;
  title: string;
  desc: string;
  category: 'voice' | 'ai' | 'security' | 'compliance' | 'analytics';
  status: 'active' | 'configured' | 'pending';
  children?: React.ReactNode;
}) {
  const [expanded, setExpanded] = useState(false);
  const catColor = {
    voice: '#22d3ee',
    ai: '#a855f7',
    security: '#e53935',
    compliance: '#f59e0b',
    analytics: '#4caf50',
  }[category];
  const statusColor = { active: '#4caf50', configured: '#29b6f6', pending: '#ff9800' }[status];
  const statusLabel = { active: 'ACTIVE', configured: 'CONFIGURED', pending: 'PENDING' }[status];
  return (
    <div
      className="bg-[#0f1720] border border-[rgba(255,255,255,0.06)] hover:border-[rgba(255,255,255,0.12)] transition-colors"
      style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
    >
      <button
        className="w-full flex items-start gap-3 p-3 text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-[9px] font-bold font-mono mt-0.5 flex-shrink-0 w-5" style={{ color: catColor }}>
          {number}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-semibold text-[rgba(255,255,255,0.85)] truncate">{title}</span>
            <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-sm flex-shrink-0" style={{ color: statusColor, background: `${statusColor}18` }}>
              {statusLabel}
            </span>
          </div>
          <div className="text-[11px] text-[rgba(255,255,255,0.4)] leading-snug">{desc}</div>
        </div>
        <span className={`text-[10px] text-[rgba(255,255,255,0.3)] flex-shrink-0 mt-0.5 transition-transform ${expanded ? 'rotate-90' : ''}`}>▶</span>
      </button>
      <AnimatePresence>
        {expanded && children && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-[rgba(255,255,255,0.05)]"
          >
            <div className="p-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const VOICE_MODULES = [
  { n: 1,   title: 'Natural Voice Realtime Engine', desc: 'Low-latency voice that sounds human, not robotic, with interruption handling.', cat: 'voice', status: 'active' },
  { n: 2,   title: 'Editable Prompt Library', desc: 'Every AI phone behavior is controlled by editable "policies" you can change.', cat: 'ai', status: 'active' },
  { n: 3,   title: 'Voice Flow Builder (Visual)', desc: 'Drag/drop nodes: greet → identify → classify → solve → escalate.', cat: 'voice', status: 'active' },
  { n: 4,   title: 'Caller Intent Classifier', desc: 'Identifies billing, onboarding, compliance, support, export, scheduling, emergencies.', cat: 'ai', status: 'active' },
  { n: 5,   title: 'Context Injection', desc: 'AI sees tenant profile + open issues before responding.', cat: 'ai', status: 'active' },
  { n: 6,   title: 'Dynamic Knowledge', desc: 'AI references current claim/export status without hallucinating; only reads from system-of-record.', cat: 'ai', status: 'active' },
  { n: 7,   title: 'Escalation Threshold Controls', desc: 'Set "confidence threshold"; below threshold AI escalates to you.', cat: 'ai', status: 'active' },
  { n: 8,   title: 'Ring-to-You Rules', desc: 'Define when calls ring your phone vs stay with AI.', cat: 'voice', status: 'active' },
  { n: 9,   title: 'Urgency Detection', desc: 'If caller sounds distressed/urgent, immediate escalation.', cat: 'ai', status: 'active' },
  { n: 10,  title: 'Identity Verification Script', desc: 'AI verifies caller role before revealing sensitive info.', cat: 'security', status: 'active' },
  { n: 11,  title: 'Script Versioning', desc: 'Every wording change is tracked; roll back instantly.', cat: 'ai', status: 'active' },
  { n: 12,  title: 'Tone Sliders', desc: 'Adjust AI tone, speed, and formality.', cat: 'voice', status: 'configured' },
  { n: 13,  title: 'Pronunciation Dictionary', desc: 'Custom pronunciations for agencies and acronyms.', cat: 'voice', status: 'configured' },
  { n: 14,  title: 'Call Summary + Tasks', desc: 'Instant summary + tasks after each call.', cat: 'ai', status: 'active' },
  { n: 15,  title: 'Disposition Codes', desc: 'Every call ends with standardized reason/outcome codes.', cat: 'analytics', status: 'active' },
  { n: 16,  title: 'Call Deflection Analytics', desc: 'Measure how many calls AI resolves without founder.', cat: 'analytics', status: 'active' },
  { n: 17,  title: 'Voice FAQ Builder', desc: 'Convert text FAQs into voice-friendly responses.', cat: 'voice', status: 'configured' },
  { n: 18,  title: 'Multi-Language Voice', desc: 'Optional bilingual support.', cat: 'voice', status: 'pending' },
  { n: 19,  title: 'Hold Music Replacement', desc: 'AI updates caller on progress ("checking claim status").', cat: 'voice', status: 'active' },
  { n: 20,  title: 'Callback Scheduling', desc: 'AI schedules callback slots when you\'re busy.', cat: 'voice', status: 'active' },
  { n: 21,  title: 'Inbound SLA Management', desc: 'Different call handling policies per tenant plan.', cat: 'compliance', status: 'active' },
  { n: 22,  title: 'Per-Tenant Greeting', desc: 'Thank you for calling {{tenant}}.', cat: 'voice', status: 'active' },
  { n: 23,  title: 'Compliance-Safe Responses', desc: 'Blocks prohibited statements and suggests safe alternatives.', cat: 'compliance', status: 'active' },
  { n: 24,  title: 'Call Recording Policies', desc: 'Per-tenant legal compliance settings.', cat: 'compliance', status: 'active' },
  { n: 25,  title: 'Silence Handling', desc: '"Are you still there?" logic without awkwardness.', cat: 'voice', status: 'active' },
  { n: 26,  title: 'Interrupt Handling', desc: 'Caller can interrupt; AI adapts mid-sentence.', cat: 'voice', status: 'active' },
  { n: 27,  title: 'Diarization', desc: 'Identifies speakers if multiple people are present.', cat: 'ai', status: 'configured' },
  { n: 28,  title: 'Keyword Spotting', desc: 'Triggers actions ("resubmit," "appeal," "export failed").', cat: 'ai', status: 'active' },
  { n: 29,  title: 'Workflow Triggers from Voice', desc: 'Voice commands launch workflows with confirmation.', cat: 'ai', status: 'active' },
  { n: 30,  title: 'Founder Whisper Mode', desc: 'AI gives you a private on-screen hint while you talk.', cat: 'ai', status: 'active' },
  { n: 31,  title: 'Queue Manager', desc: 'Multiple callers; AI triages.', cat: 'voice', status: 'active' },
  { n: 32,  title: 'Escalation Warm Transfer', desc: 'AI briefs you before transfer.', cat: 'voice', status: 'active' },
  { n: 33,  title: 'Cold Transfer Blocker', desc: 'Prevents dumping calls on you with no context.', cat: 'voice', status: 'active' },
  { n: 34,  title: 'Schedule-Aware Routing', desc: 'Respects your calendar and focus blocks.', cat: 'ai', status: 'active' },
  { n: 35,  title: 'After-Hours Policy Engine', desc: 'AI fully handles after-hours with strict rules.', cat: 'ai', status: 'active' },
  { n: 36,  title: 'Live Compliance Monitor', desc: 'Flags phrases that might create liability.', cat: 'compliance', status: 'active' },
  { n: 37,  title: 'Caller Satisfaction Capture', desc: 'Quick voice survey after resolution.', cat: 'analytics', status: 'configured' },
  { n: 38,  title: 'Call-to-Ticket Converter', desc: 'Auto-creates ticket when unresolved.', cat: 'ai', status: 'active' },
  { n: 39,  title: 'Voice Notes to CRM', desc: 'Voice memos saved and linked.', cat: 'ai', status: 'active' },
  { n: 40,  title: 'Spam Call Shield', desc: 'Blocks robocalls.', cat: 'security', status: 'active' },
  { n: 41,  title: 'VIP Routing', desc: 'High priority clients get direct escalation.', cat: 'voice', status: 'active' },
  { n: 42,  title: 'Onboarding Call Assistant', desc: 'Guided onboarding checklist during calls.', cat: 'ai', status: 'active' },
  { n: 43,  title: 'Billing Call Assistant', desc: 'Guided denial/claim checklist during calls.', cat: 'ai', status: 'active' },
  { n: 44,  title: 'Export Support Assistant', desc: 'Guided NEMSIS export troubleshooting.', cat: 'ai', status: 'active' },
  { n: 45,  title: 'Compliance Call Assistant', desc: 'Guided accreditation/DEA/CMS safe responses.', cat: 'compliance', status: 'active' },
  { n: 46,  title: 'Voice Personalization Tokens', desc: 'Remembers preferences ("call me Chief").', cat: 'voice', status: 'active' },
  { n: 47,  title: 'Call Outcome Prediction', desc: 'Predicts likely resolution and advises.', cat: 'analytics', status: 'configured' },
  { n: 48,  title: 'Script Testing Sandbox', desc: 'Test new scripts against simulated callers.', cat: 'ai', status: 'active' },
  { n: 49,  title: 'A/B Script Experiments', desc: 'Optimize greeting and flows.', cat: 'analytics', status: 'configured' },
  { n: 50,  title: 'Silence-to-Text Follow-up', desc: 'If caller drops, AI texts a follow-up link.', cat: 'voice', status: 'active' },
  { n: 51,  title: 'Document Request by Voice', desc: '"Please text your facesheet to this number."', cat: 'voice', status: 'active' },
  { n: 52,  title: 'Speech-to-Structured Data', desc: 'Extracts claim ID, incident number, payer type.', cat: 'ai', status: 'active' },
  { n: 53,  title: 'Error-Proof Confirmation', desc: 'AI repeats critical identifiers for confirmation.', cat: 'ai', status: 'active' },
  { n: 54,  title: 'No-Data Hallucination Mode', desc: "If system doesn't know, AI says so and creates a task.", cat: 'ai', status: 'active' },
  { n: 55,  title: 'Call Rate Controls', desc: 'Prevents runaway AI usage costs.', cat: 'analytics', status: 'active' },
  { n: 56,  title: 'Call Cost Dashboard', desc: 'Costs per channel and per tenant.', cat: 'analytics', status: 'active' },
  { n: 57,  title: 'High-Quality Voice Selection', desc: 'Avoids generic voices by design.', cat: 'voice', status: 'active' },
  { n: 58,  title: 'Audio Quality Controls', desc: 'Noise suppression, echo cancellation.', cat: 'voice', status: 'active' },
  { n: 59,  title: 'Call Recording Encryption', desc: 'Encrypted at rest and access-controlled.', cat: 'security', status: 'active' },
  { n: 60,  title: 'Retention Policies', desc: 'Retention by category (support vs compliance).', cat: 'compliance', status: 'active' },
  { n: 61,  title: 'Founder "Do Not Disturb"', desc: 'AI handles everything unless urgent.', cat: 'ai', status: 'active' },
  { n: 62,  title: 'Urgent Override', desc: 'Urgent calls always ring through.', cat: 'voice', status: 'active' },
  { n: 63,  title: 'Call Reason Pre-Menu', desc: 'Say "billing" or "support."', cat: 'voice', status: 'active' },
  { n: 64,  title: 'Smart Menu Skipping', desc: 'If AI detects intent, skips menus.', cat: 'ai', status: 'active' },
  { n: 65,  title: 'Caller Context Auto-Fetch', desc: 'While the caller speaks, the system pulls tenant profile, open tickets, last claim status, outstanding invoices, export failures, and recent messages — AI answers with verified facts only.', cat: 'ai', status: 'active' },
  { n: 66,  title: 'Real-Time Ring + Screen Pop', desc: 'When a call hits, your dashboard and phone both ring with a screen pop showing caller, role, urgency score, and AI\'s suggested first sentence.', cat: 'voice', status: 'active' },
  { n: 67,  title: 'Smart Alert Policies', desc: 'Configurable rules: ring-only for VIP tenants, silent notifications for low priority, escalate after 2 missed calls, night mode with only compliance emergencies breaking through.', cat: 'ai', status: 'active' },
  { n: 68,  title: 'Per-Tenant Script Packs', desc: 'Every tenant has a tailored phone-tree pack (different terms, local policies, operational vocabulary), preventing generic responses.', cat: 'ai', status: 'active' },
  { n: 69,  title: 'Voice Compliance Guard Mode', desc: 'For CMS/DEA-sensitive topics, AI switches to strict phrasing patterns, asks fewer open-ended questions, and logs every step for audit defensibility.', cat: 'compliance', status: 'active' },
  { n: 70,  title: 'AI Billing Concierge Mode', desc: 'AI answers status questions like "Was claim 123 submitted?" using system-of-record, then offers next steps ("we\'re waiting on EOB; expected in 7–10 days").', cat: 'ai', status: 'active' },
  { n: 71,  title: 'AI Onboarding Concierge Mode', desc: 'AI guides new agencies through onboarding steps (BAA, payer setup, user roles, exports) and schedules your involvement only where required.', cat: 'ai', status: 'active' },
  { n: 72,  title: 'AI Export Support Mode', desc: 'AI walks through export validation: which dataset version, which file failed, what field groups error, then generates a repair checklist.', cat: 'ai', status: 'active' },
  { n: 73,  title: 'AI Scheduling Support Mode', desc: 'AI assists with shift scheduling questions, credential expiration issues, and pushes "suggested schedule fixes" based on staffing constraints.', cat: 'ai', status: 'configured' },
  { n: 74,  title: 'Call-to-Workflow Confirmation', desc: 'Before AI triggers actions (resubmission, invoice resend, export retry), it reads back the intent and requires explicit confirmation ("Say confirm to proceed").', cat: 'ai', status: 'active' },
  { n: 75,  title: 'Call Summaries with Decision Trace', desc: 'Summaries include what was said, what data was referenced, what rule triggered what action, and what permissions allowed it (for audits).', cat: 'compliance', status: 'active' },
  { n: 76,  title: 'Escalation Ladder with Proof', desc: 'AI escalates only after: (a) verified identity, (b) checked system status, (c) tried approved remedies, (d) packaged a crisp summary for you.', cat: 'ai', status: 'active' },
  { n: 77,  title: 'Adaptive Prompts by Role', desc: 'Same question yields different AI responses depending on caller role (agency admin vs provider), reducing confusion and preventing over-disclosure.', cat: 'ai', status: 'active' },
  { n: 78,  title: 'Priority Scoring Engine', desc: 'Assigns each call a priority score combining revenue impact, compliance risk, tenant tier, aging denials, and sentiment urgency.', cat: 'analytics', status: 'active' },
  { n: 79,  title: 'Voice Denial Reason Explainer', desc: 'AI explains denial reasons in plain English and gives a structured fix plan, mapped to your internal denial playbooks.', cat: 'ai', status: 'active' },
  { n: 80,  title: 'Appeal Draft Trigger (Voice)', desc: 'If caller says "appeal," AI creates an appeal task and drafts the outline instantly (without fabricating facts), then routes for your approval.', cat: 'ai', status: 'active' },
  { n: 81,  title: 'Smart Hold Behavior', desc: 'Instead of "please hold," AI narrates what it\'s doing: "I\'m pulling the claim status now," then returns with verified results.', cat: 'voice', status: 'active' },
  { n: 82,  title: 'Dead-Air Recovery', desc: 'Detects silence, prompts politely, offers options ("say billing or export"), and if still silent, offers callback/SMS fallback.', cat: 'voice', status: 'active' },
  { n: 83,  title: 'Fallback Channel Switch', desc: 'If a call drops, AI automatically sends a text with next steps and a secure link to upload docs or schedule a meeting.', cat: 'voice', status: 'active' },
  { n: 84,  title: 'Speech-to-Fields Extractor', desc: 'Extracts claim IDs, incident numbers, payer names, dates, and keywords into structured fields to reduce your manual entry.', cat: 'ai', status: 'active' },
  { n: 85,  title: 'Error-Resistant Confirmation', desc: 'AI repeats critical identifiers back ("That\'s incident 2026-0142, correct?") to prevent expensive mistakes.', cat: 'ai', status: 'active' },
  { n: 86,  title: 'Secure Disclosure Rules', desc: 'AI will not disclose claim details unless identity+role checks pass, and will always present minimal necessary info based on role.', cat: 'security', status: 'active' },
  { n: 87,  title: 'Prompt Injection Defense', desc: 'The voice agent resists "ignore your rules" attempts, refusing to reveal secrets or privileged system details.', cat: 'security', status: 'active' },
  { n: 88,  title: 'Policy-Aware Knowledge Boundaries', desc: 'AI can answer platform questions, but refuses medical advice, and refuses anything outside its allowed scope.', cat: 'compliance', status: 'active' },
  { n: 89,  title: 'On-Call Escalation Paging', desc: 'For critical failures (exports down, billing pipeline outage), AI can page you with persistent alerts until acknowledged.', cat: 'voice', status: 'active' },
  { n: 90,  title: 'Founder Busy Adaptive Mode', desc: 'When you\'re busy, AI tightens responses, defers non-urgent items, batches tasks, and schedules them for later review.', cat: 'ai', status: 'active' },
  { n: 91,  title: 'Callback Slot Optimizer', desc: 'Chooses callback slots based on your calendar, task load, tenant time zones, and urgency — then books automatically.', cat: 'ai', status: 'active' },
  { n: 92,  title: 'Voice Analytics & Coaching', desc: 'Shows call outcomes, script branch performance, where callers get stuck, and suggests exactly which script nodes to improve.', cat: 'analytics', status: 'active' },
  { n: 93,  title: 'A/B Testing for Scripts', desc: 'Runs controlled experiments: two greetings, two flows, two confirmation styles — measures resolution rate and caller satisfaction.', cat: 'analytics', status: 'configured' },
  { n: 94,  title: 'Latency & Quality Monitor', desc: 'Tracks voice latency, jitter, and transcription error rate; auto-switches to best region/route for cleaner calls.', cat: 'analytics', status: 'active' },
  { n: 95,  title: 'Cost Control Governor', desc: 'Prevents runaway AI costs with caps per tenant/per hour, and "degrade gracefully" strategies (text follow-ups instead of long calls).', cat: 'analytics', status: 'active' },
  { n: 96,  title: 'Voice Memory (Safe, Scoped)', desc: 'Remembers safe preferences ("call me Josh," "we prefer email") without storing sensitive content; tenant-scoped only.', cat: 'ai', status: 'active' },
  { n: 97,  title: 'Call Recording Governance', desc: 'Configurable rules by state/tenant, consent prompts, encryption, retention windows, and access logs.', cat: 'compliance', status: 'active' },
  { n: 98,  title: 'Incident Mode War Room', desc: 'During major incidents, all calls route to a dedicated flow, status page updates auto-send, and your dashboard locks into incident priority view.', cat: 'voice', status: 'active' },
  { n: 99,  title: 'Human-in-the-Loop Review Queue', desc: 'AI flags "low confidence" calls into a review queue with transcript + recommended response for you to approve quickly.', cat: 'ai', status: 'active' },
  { n: 100, title: 'Continuous Improvement Loop', desc: 'Every failure becomes a structured learning ticket: what went wrong, which rule/script was missing, what change fixes it, and how to validate it safely.', cat: 'ai', status: 'active' },
] as const;

type FilterCat = 'all' | 'voice' | 'ai' | 'security' | 'compliance' | 'analytics';
type FilterStatus = 'all' | 'active' | 'configured' | 'pending';

export default function PhoneSystemPage() {
  const [catFilter, setCatFilter] = useState<FilterCat>('all');
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<'modules' | 'queue' | 'flow' | 'analytics'>('modules');

  const filtered = VOICE_MODULES.filter((m) => {
    if (catFilter !== 'all' && m.cat !== catFilter) return false;
    if (statusFilter !== 'all' && m.status !== statusFilter) return false;
    if (search && !m.title.toLowerCase().includes(search.toLowerCase()) && !m.desc.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="p-5 space-y-6 min-h-screen">
      <PageHeader />
      <KpiStrip />

      <div className="flex gap-1 border-b border-[rgba(255,255,255,0.06)] pb-0">
        {([
          { key: 'modules', label: 'All 100 Modules' },
          { key: 'queue', label: 'Call Queue' },
          { key: 'flow', label: 'Script Flow Preview' },
          { key: 'analytics', label: 'Voice Analytics' },
        ] as { key: typeof activeTab; label: string }[]).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`h-8 px-4 text-[11px] font-semibold uppercase tracking-wider transition-colors border-b-2 -mb-px ${
              activeTab === tab.key
                ? 'text-[#ff6b1a] border-[#ff6b1a]'
                : 'text-[rgba(255,255,255,0.4)] border-transparent hover:text-[rgba(255,255,255,0.7)]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'queue' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)' }}>
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,255,255,0.38)]">MODULE 31 · Live Call Queue</span>
              <span className="text-[9px] bg-[rgba(34,211,238,0.1)] text-[#22d3ee] px-2 py-0.5 uppercase tracking-wider font-bold">3 CALLERS</span>
            </div>
            <table className="w-full">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.05)]">
                  {['#', 'Caller', 'Intent', 'Wait', 'Priority', 'AI Can Resolve'].map((h) => (
                    <th key={h} className="text-left text-[9px] uppercase tracking-wider text-[rgba(255,255,255,0.3)] pb-2 pr-3 font-semibold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <CallQueueRow position={1} caller="Metro EMS — Billing" intent="Denial / Code 97" wait="0:42" score={88} aiCanResolve={false} />
                <CallQueueRow position={2} caller="Valley Ambulance" intent="Export Support" wait="1:15" score={52} aiCanResolve={true} />
                <CallQueueRow position={3} caller="Unknown — New Caller" intent="Onboarding" wait="2:04" score={25} aiCanResolve={true} />
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {activeTab === 'flow' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)' }}>
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,255,255,0.38)]">MODULE 3 · Billing Call Script Flow (Preview)</span>
              <button className="h-6 px-2.5 bg-[rgba(255,107,26,0.12)] border border-[rgba(255,107,26,0.25)] text-[#ff6b1a] text-[10px] font-semibold rounded-sm hover:bg-[rgba(255,107,26,0.2)] transition-colors">
                Open Flow Builder
              </button>
            </div>
            <div className="font-mono space-y-0.5">
              <ScriptNode type="trigger" label="Inbound call received" />
              <ScriptNode type="action" label="Fetch tenant context (profile, open tickets, last claim)" indent={1} />
              <ScriptNode type="action" label="Play per-tenant greeting: 'Thank you for calling {{tenant}}…'" indent={1} />
              <ScriptNode type="condition" label="Caller says 'billing' or intent classifier → BILLING" indent={1} />
              <ScriptNode type="action" label="Request identity verification (PIN or last 4 of account)" indent={2} />
              <ScriptNode type="condition" label="Identity verified?" indent={2} />
              <ScriptNode type="action" label="Ask: 'What claim or denial are you calling about?'" indent={3} />
              <ScriptNode type="action" label="Extract claim ID via speech-to-fields" indent={3} />
              <ScriptNode type="action" label="Read claim status from system-of-record (no hallucination)" indent={3} />
              <ScriptNode type="condition" label="Claim denied?" indent={3} />
              <ScriptNode type="action" label="Explain denial in plain English + offer fix plan" indent={4} />
              <ScriptNode type="condition" label="Caller asks for appeal?" indent={4} />
              <ScriptNode type="action" label="Create appeal task + draft outline → route for approval" indent={5} />
              <ScriptNode type="condition" label="AI confidence < threshold?" indent={3} />
              <ScriptNode type="escalate" label="Warm transfer to founder with summary + context" indent={4} />
            </div>
          </div>
        </motion.div>
      )}

      {activeTab === 'analytics' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">MODULE 16 · AI Deflection Rate</div>
              {[
                { label: 'Billing inquiries', deflected: 91 },
                { label: 'Export support', deflected: 78 },
                { label: 'Onboarding questions', deflected: 85 },
                { label: 'Denial explanations', deflected: 72 },
                { label: 'Scheduling support', deflected: 88 },
              ].map((item) => (
                <div key={item.label} className="mb-2">
                  <div className="flex justify-between text-[11px] mb-0.5">
                    <span className="text-[rgba(255,255,255,0.55)]">{item.label}</span>
                    <span className="font-semibold text-[#22d3ee]">{item.deflected}%</span>
                  </div>
                  <div className="h-1 bg-[rgba(255,255,255,0.06)] rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-[#22d3ee]" style={{ width: `${item.deflected}%` }} />
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">MODULE 94 · Latency & Quality</div>
              {[
                { label: 'Voice latency (p50)', value: '180ms', ok: true },
                { label: 'Voice latency (p99)', value: '310ms', ok: true },
                { label: 'Transcript error rate', value: '1.2%', ok: true },
                { label: 'Audio jitter', value: '8ms', ok: true },
                { label: 'Noise suppression', value: 'Active', ok: true },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between py-1.5 border-b border-[rgba(255,255,255,0.05)] last:border-0">
                  <span className="text-[11px] text-[rgba(255,255,255,0.55)]">{item.label}</span>
                  <span className="text-[11px] font-semibold" style={{ color: item.ok ? '#4caf50' : '#e53935' }}>{item.value}</span>
                </div>
              ))}
            </div>

            <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">MODULE 56 · Cost per Tenant</div>
              {[
                { tenant: 'Metro EMS', cost: '$3.84', calls: 47 },
                { tenant: 'Valley Amb.', cost: '$1.62', calls: 22 },
                { tenant: 'Tri-County', cost: '$2.11', calls: 31 },
                { tenant: 'City Hosp.', cost: '$0.74', calls: 9 },
              ].map((item) => (
                <div key={item.tenant} className="flex items-center gap-3 py-1.5 border-b border-[rgba(255,255,255,0.05)] last:border-0">
                  <span className="flex-1 text-[11px] text-[rgba(255,255,255,0.65)]">{item.tenant}</span>
                  <span className="text-[10px] text-[rgba(255,255,255,0.35)]">{item.calls} calls</span>
                  <span className="text-xs font-semibold text-[#22d3ee]">{item.cost}</span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {activeTab === 'modules' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <span className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)]">FILTER:</span>
            <div className="flex gap-1 flex-wrap">
              {(['all', 'voice', 'ai', 'analytics', 'compliance', 'security'] as FilterCat[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setCatFilter(f)}
                  className={`h-6 px-2.5 text-[10px] uppercase tracking-wider font-semibold transition-colors rounded-sm ${
                    catFilter === f ? 'bg-[#ff6b1a] text-black' : 'bg-[rgba(255,255,255,0.05)] text-[rgba(255,255,255,0.45)] hover:text-white'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            <div className="flex gap-1">
              {(['all', 'active', 'configured', 'pending'] as FilterStatus[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setStatusFilter(f)}
                  className={`h-6 px-2.5 text-[10px] uppercase tracking-wider font-semibold transition-colors rounded-sm ${
                    statusFilter === f ? 'bg-[rgba(255,255,255,0.15)] text-white' : 'bg-[rgba(255,255,255,0.04)] text-[rgba(255,255,255,0.35)] hover:text-white'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search modules..."
              className="h-6 bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] px-2 text-[11px] text-white placeholder-[rgba(255,255,255,0.25)] focus:outline-none focus:border-[rgba(255,107,26,0.4)] rounded-sm flex-1 min-w-[120px]"
            />
            <span className="text-[10px] text-[rgba(255,255,255,0.3)] ml-auto">{filtered.length} / 100 modules</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
            {filtered.map((m) => (
              <ModuleCard
                key={m.n}
                number={m.n}
                title={m.title}
                desc={m.desc}
                category={m.cat as 'voice' | 'ai' | 'security' | 'compliance' | 'analytics'}
                status={m.status as 'active' | 'configured' | 'pending'}
              >
                <div className="space-y-2">
                  <div className="text-[11px] text-[rgba(255,255,255,0.5)] leading-relaxed">{m.desc}</div>
                  <div className="flex gap-2">
                    <button className="h-6 px-2.5 bg-[rgba(255,107,26,0.12)] border border-[rgba(255,107,26,0.25)] text-[#ff6b1a] text-[10px] font-semibold rounded-sm hover:bg-[rgba(255,107,26,0.2)] transition-colors">
                      Configure
                    </button>
                    <button className="h-6 px-2.5 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.08)] text-[rgba(255,255,255,0.5)] text-[10px] rounded-sm hover:text-white transition-colors">
                      View Logs
                    </button>
                  </div>
                </div>
              </ModuleCard>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
