'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function PageHeader({ title, sub, moduleRange }: { title: string; sub: string; moduleRange: string }) {
  return (
    <div className="hud-rail pb-3 mb-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">
            CATEGORY 1 · MODULES {moduleRange}
          </div>
          <h1 className="text-lg font-black uppercase tracking-wider text-white">{title}</h1>
          <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">{sub}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#4caf50] animate-pulse" />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#4caf50]">LIVE</span>
        </div>
      </div>
    </div>
  );
}

function KpiStrip({ items }: { items: { label: string; value: string; color?: string; trend?: 'up' | 'down' | 'flat' }[] }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 mb-6">
      {items.map((item) => (
        <div
          key={item.label}
          className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-3"
          style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
        >
          <div className="text-[9px] uppercase tracking-widest text-[rgba(255,255,255,0.35)] mb-1">{item.label}</div>
          <div className="text-lg font-bold" style={{ color: item.color ?? 'white' }}>{item.value}</div>
          {item.trend && (
            <div className="text-[10px] mt-0.5" style={{ color: item.trend === 'up' ? '#4caf50' : item.trend === 'down' ? '#e53935' : 'rgba(255,255,255,0.3)' }}>
              {item.trend === 'up' ? '▲' : item.trend === 'down' ? '▼' : '—'}
            </div>
          )}
        </div>
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
  category: 'comms' | 'ai' | 'security' | 'compliance' | 'voice';
  status: 'active' | 'configured' | 'pending';
  children?: React.ReactNode;
}) {
  const [expanded, setExpanded] = useState(false);
  const catColor = {
    comms: '#4caf50',
    ai: '#a855f7',
    security: '#e53935',
    compliance: '#f59e0b',
    voice: '#22d3ee',
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

function ConversationThread({ from, channel, time, preview, sentiment, urgent }: {
  from: string; channel: string; time: string; preview: string; sentiment: 'positive' | 'neutral' | 'negative'; urgent: boolean;
}) {
  const sentColor = { positive: '#4caf50', neutral: 'rgba(255,255,255,0.38)', negative: '#e53935' }[sentiment];
  return (
    <div className={`flex items-start gap-3 py-2.5 border-b border-[rgba(255,255,255,0.05)] last:border-0 ${urgent ? 'bg-[rgba(229,57,53,0.04)]' : ''}`}>
      {urgent && <span className="text-[8px] text-[#e53935] font-bold mt-1.5 flex-shrink-0">!</span>}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs font-semibold text-white">{from}</span>
          <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 bg-[rgba(255,255,255,0.05)] text-[rgba(255,255,255,0.4)] rounded-sm">{channel}</span>
          {urgent && <span className="text-[9px] text-[#e53935] font-bold uppercase">URGENT</span>}
        </div>
        <div className="text-[11px] text-[rgba(255,255,255,0.5)] truncate">{preview}</div>
      </div>
      <div className="flex flex-col items-end gap-1 flex-shrink-0">
        <span className="text-[10px] text-[rgba(255,255,255,0.3)]">{time}</span>
        <span className="w-1.5 h-1.5 rounded-full" style={{ background: sentColor }} />
      </div>
    </div>
  );
}

function SLARow({ tenant, channel, firstResponse, sla, breached }: {
  tenant: string; channel: string; firstResponse: string; sla: string; breached: boolean;
}) {
  return (
    <tr className={breached ? 'bg-[rgba(229,57,53,0.06)]' : ''}>
      <td className="py-2 pr-4 text-xs text-[rgba(255,255,255,0.75)]">{tenant}</td>
      <td className="py-2 pr-4 text-[11px] text-[rgba(255,255,255,0.45)] uppercase">{channel}</td>
      <td className="py-2 pr-4 text-xs" style={{ color: breached ? '#e53935' : '#4caf50' }}>{firstResponse}</td>
      <td className="py-2 text-[11px] text-[rgba(255,255,255,0.4)]">{sla}</td>
      <td className="py-2 pl-2">
        <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-sm ${breached ? 'text-[#e53935] bg-[rgba(229,57,53,0.15)]' : 'text-[#4caf50] bg-[rgba(76,175,80,0.12)]'}`}>
          {breached ? 'BREACHED' : 'OK'}
        </span>
      </td>
    </tr>
  );
}

const COMM_MODULES = [
  { n: 1,  title: 'Unified Conversation Graph', desc: 'Merges SMS/RCS/email/voice/video into one threaded case timeline per tenant + incident. Auto-links messages by phone/email/domain and shows cause→effect (denial → call → fix → resubmission).', cat: 'comms', status: 'active' },
  { n: 2,  title: 'RCS Smart Composer', desc: 'Suggests rich cards (quick replies, forms, attachments) based on intent — "need facesheet" → one-tap upload request.', cat: 'comms', status: 'active' },
  { n: 3,  title: 'Two-Way SMS with Compliance Guardrails', desc: 'Blocks sending PHI if policy forbids, auto-redacts detected identifiers, and offers safer phrasing alternatives.', cat: 'compliance', status: 'active' },
  { n: 4,  title: 'Tenant-Specific Tone Profiles', desc: 'Each tenant has a preferred communication tone; AI auto-matches language for fire admin vs hospital billing vs compliance officer.', cat: 'ai', status: 'configured' },
  { n: 5,  title: 'Real-Time Ring-in-Dashboard Softphone', desc: 'Incoming calls ring with caller context panel (tenant, open issues, unpaid invoice, last denial) before you answer.', cat: 'voice', status: 'active' },
  { n: 6,  title: 'Adaptive Call Routing', desc: 'Routes calls to AI, to you, or to voicemail based on your calendar status + urgency score + tenant tier.', cat: 'ai', status: 'active' },
  { n: 7,  title: 'AI Phone Tree Script Editor', desc: 'Visual flow editor: "If caller says denial → ask claim ID → read status → offer next steps → escalate."', cat: 'ai', status: 'configured' },
  { n: 8,  title: 'Live Script Hot-Swap', desc: 'Edit what AI says and changes apply immediately without redeploy — versioned with rollback.', cat: 'ai', status: 'active' },
  { n: 9,  title: 'Natural Voice Persona Library', desc: 'Multiple high-quality voices mapped to use-cases (support vs billing vs compliance) with pacing/verbosity controls.', cat: 'voice', status: 'configured' },
  { n: 10, title: 'Voice Safety & Compliance Filter', desc: 'Prohibits AI from promising medical advice; enforces billing-only scope; logs prohibited attempts.', cat: 'compliance', status: 'active' },
  { n: 11, title: 'Call Transcription + Action Extraction', desc: 'Auto-generates tasks ("send BAA," "request missing PCS") and schedules follow-ups.', cat: 'ai', status: 'active' },
  { n: 12, title: 'Call Outcome Scoring', desc: 'Measures resolution rate, escalation rate, call length, and customer sentiment; recommends script improvements.', cat: 'ai', status: 'active' },
  { n: 13, title: 'Voicemail-to-Ticket Conversion', desc: 'Voicemails become structured tickets with priority and suggested response.', cat: 'comms', status: 'active' },
  { n: 14, title: 'SMS-to-Workflow Trigger', desc: 'Text "RESUBMIT 123" triggers billing workflow with audit trail.', cat: 'comms', status: 'active' },
  { n: 15, title: 'Attachment Intake Routing', desc: 'Images/PDFs attached via SMS/email auto-classified (facesheet vs EOB vs denial letter) and routed to correct module.', cat: 'ai', status: 'active' },
  { n: 16, title: 'Fax Ingestion Hub', desc: 'Faxes become searchable documents, auto-labeled, linked to patient/claim without storing patient financial data.', cat: 'comms', status: 'active' },
  { n: 17, title: 'Multi-Channel Broadcast Announcements', desc: 'Send outage notices or onboarding reminders to all tenants with per-tenant scheduling.', cat: 'comms', status: 'active' },
  { n: 18, title: 'Priority Inbox', desc: 'AI prioritizes messages by revenue impact + compliance risk + aging + VIP status.', cat: 'ai', status: 'active' },
  { n: 19, title: 'Auto-Reply Templates with Variables', desc: '"Hi {{name}}, we received your {{document_type}} for claim {{claim}}…"', cat: 'comms', status: 'configured' },
  { n: 20, title: 'SLA Timers + Escalation', desc: 'Timers start at first inbound; if SLA breached, AI drafts response + escalates to you.', cat: 'compliance', status: 'active' },
  { n: 21, title: 'Sentiment + Urgency Detection', desc: 'Flags angry, urgent, legal-risk messages and recommends safest response.', cat: 'ai', status: 'active' },
  { n: 22, title: 'Conversation Audit Log', desc: 'Immutable record of all comms — what was said, by AI or founder, and why.', cat: 'compliance', status: 'active' },
  { n: 23, title: 'Communication Consent Manager', desc: 'Tracks opt-in/opt-out for SMS/RCS; enforces compliance automatically.', cat: 'compliance', status: 'active' },
  { n: 24, title: 'Quiet Hours & Time-Zone Awareness', desc: "Auto-schedules messages within tenant's local time policies.", cat: 'comms', status: 'active' },
  { n: 25, title: 'One-Click Google Meet Link Generator', desc: 'Creates meeting link, inserts agenda, sends invites, and adds CRM notes.', cat: 'comms', status: 'active' },
  { n: 26, title: 'WebRTC Secure Video Room', desc: 'Instant secure video room from dashboard; no client account needed; one-time links.', cat: 'comms', status: 'configured' },
  { n: 27, title: 'Screen Share + Co-Browse', desc: "With consent, view client's portal screen for support (no PHI shown unless authorized).", cat: 'security', status: 'configured' },
  { n: 28, title: 'Remote Assist Session Recorder', desc: 'Records session metadata and decisions for compliance audits.', cat: 'compliance', status: 'configured' },
  { n: 29, title: 'AI Moderator for Video Calls', desc: 'Listens, summarizes, captures action items live, and drafts follow-up email.', cat: 'ai', status: 'pending' },
  { n: 30, title: 'Meeting Intake Form Builder', desc: "AI sends pre-call form ('what's broken?'), reducing call time for a solo operator.", cat: 'ai', status: 'configured' },
  { n: 31, title: 'Thread-to-Case Linking', desc: 'Any message thread can be linked to claim, accreditation item, export issue, or support ticket.', cat: 'comms', status: 'active' },
  { n: 32, title: 'Auto-Translate Mode', desc: 'Translates inbound messages and suggests bilingual replies when needed.', cat: 'comms', status: 'pending' },
  { n: 33, title: 'Attachment Redaction Tool', desc: 'Auto-redacts sensitive identifiers in shared screenshots before forwarding.', cat: 'security', status: 'active' },
  { n: 34, title: 'Communication KPI Dashboard', desc: 'First response time, resolution time, channels used, top intents.', cat: 'comms', status: 'active' },
  { n: 35, title: 'Intent Taxonomy Manager', desc: 'Define intents ("PCS request," "NEMSIS error," "Stripe failure") and map automations.', cat: 'ai', status: 'configured' },
  { n: 36, title: 'AI Autopilot — Handle Common Questions', desc: 'AI resolves common billing/status questions without escalating.', cat: 'ai', status: 'active' },
  { n: 37, title: 'Founder Override Hotkey', desc: 'Instant takeover of AI phone/chat with one keystroke.', cat: 'voice', status: 'active' },
  { n: 38, title: 'Caller Authentication Prompts', desc: 'AI verifies caller identity (tenant PIN / code) before revealing sensitive statuses.', cat: 'security', status: 'active' },
  { n: 39, title: 'Per-Tenant Contact Directory', desc: 'Roles, phone, email, escalation chain; AI uses it automatically.', cat: 'comms', status: 'active' },
  { n: 40, title: 'Smart Reminders', desc: '"You promised to send X" reminders to you and the tenant.', cat: 'ai', status: 'active' },
  { n: 41, title: 'Outbound Campaign Manager', desc: 'Onboarding campaigns, upgrade offers, compliance reminders with A/B testing.', cat: 'comms', status: 'configured' },
  { n: 42, title: 'RCS Read-Receipt Analytics', desc: 'Track read rates and optimize messaging.', cat: 'comms', status: 'active' },
  { n: 43, title: 'Auto-Generate Support Articles', desc: 'Converts repeated issues into knowledge base articles.', cat: 'ai', status: 'pending' },
  { n: 44, title: 'Context-Aware Signature', desc: 'AI signs messages consistently with correct compliance disclaimers.', cat: 'compliance', status: 'active' },
  { n: 45, title: 'Emergency Incident Mode', desc: 'Major outage or high severity issue locks comms into incident workflow.', cat: 'security', status: 'active' },
  { n: 46, title: 'Communication Cost Monitor', desc: 'Shows per-channel costs; recommends cheapest channel that meets SLA.', cat: 'comms', status: 'active' },
  { n: 47, title: 'Smart Routing by Topic', desc: 'Billing messages go to billing AI; scheduling issues go to scheduling AI.', cat: 'ai', status: 'active' },
  { n: 48, title: '"Do Not Disclose PHI" Switch', desc: 'Global toggle for sensitive periods; AI enforces strictest policy.', cat: 'security', status: 'active' },
  { n: 49, title: 'Proof-of-Delivery Capture', desc: 'Stores delivery confirmations for compliance communications.', cat: 'compliance', status: 'active' },
  { n: 50, title: 'Tenant Satisfaction Pulse', desc: 'Periodic AI-driven short survey; flags churn risk automatically.', cat: 'ai', status: 'configured' },
  { n: 51, title: 'Voice Menu Personalization per Tenant', desc: 'Greeting includes tenant name and current status items.', cat: 'voice', status: 'active' },
  { n: 52, title: 'Conversation-Driven Feature Requests', desc: 'AI detects "missing feature" requests and drafts backlog tickets.', cat: 'ai', status: 'pending' },
  { n: 53, title: 'Call Record Search', desc: 'Search transcripts by claim ID, denial reason, or keyword.', cat: 'comms', status: 'active' },
  { n: 54, title: 'Smart Call Summaries into CRM', desc: 'Auto-logs to tenant profile with tags.', cat: 'ai', status: 'active' },
  { n: 55, title: 'Escalation Ladder', desc: '"AI → founder → scheduled meeting" with automatic scheduling.', cat: 'ai', status: 'active' },
  { n: 56, title: 'RCS File Collection', desc: 'One-tap capture for documents; auto-links to claim.', cat: 'comms', status: 'active' },
  { n: 57, title: 'Spam + Fraud Filtering', desc: 'Blocks suspicious callers/messages; flags potential abuse.', cat: 'security', status: 'active' },
  { n: 58, title: 'Compliance Communication Packets', desc: 'Generates standardized messages for audits and accreditation items.', cat: 'compliance', status: 'configured' },
  { n: 59, title: 'Outbound Dialer (Founder-Controlled)', desc: 'Power dial for outreach with context cards.', cat: 'voice', status: 'configured' },
  { n: 60, title: 'AI Coaching for You', desc: 'Suggests best next sentence during calls based on policies.', cat: 'ai', status: 'pending' },
  { n: 61, title: 'Canned Denial Response Kits', desc: 'Multi-step playbooks triggered by denial codes.', cat: 'comms', status: 'active' },
  { n: 62, title: 'Multi-Channel Failover', desc: 'If SMS fails, switch to email automatically.', cat: 'comms', status: 'active' },
  { n: 63, title: 'Message Scheduling with Dependencies', desc: '"Send after invoice paid" or "send after export success."', cat: 'comms', status: 'configured' },
  { n: 64, title: 'Per-Agency Branding', desc: 'Outbound proposals and messages can include tenant logo (if desired).', cat: 'comms', status: 'configured' },
  { n: 65, title: 'Secure Link Vault', desc: 'Meeting links, contracts, BAA links — always expiring.', cat: 'security', status: 'active' },
  { n: 66, title: 'Retention Policies', desc: 'Configurable retention for transcripts/recordings; audits preserved longer.', cat: 'compliance', status: 'active' },
  { n: 67, title: 'Role-Based Communication Access', desc: "Founder sees all; tenant admins see their own; billing staff limited.", cat: 'security', status: 'active' },
  { n: 68, title: 'Communication Templates Versioning', desc: 'Change log + rollback for wording.', cat: 'comms', status: 'active' },
  { n: 69, title: 'AI Explain Like I\'m Busy Mode', desc: 'Ultra-short summaries and action buttons.', cat: 'ai', status: 'active' },
  { n: 70, title: 'Thread SLA Auto-Tagging', desc: 'Tags "urgent," "billing," "compliance," "export."', cat: 'compliance', status: 'active' },
  { n: 71, title: 'Auto-Generate Meeting Minutes', desc: 'From calls/video; structured format.', cat: 'ai', status: 'configured' },
  { n: 72, title: 'Multi-Attendee Notifier', desc: "Notifies the right contacts when there's a billing issue.", cat: 'comms', status: 'active' },
  { n: 73, title: 'Smart Contact Suggestions', desc: 'Suggests who to involve based on issue type.', cat: 'ai', status: 'active' },
  { n: 74, title: 'Data Loss Prevention Scans', desc: 'Detects PHI/financial content leaving system incorrectly.', cat: 'security', status: 'active' },
  { n: 75, title: 'In-App Notifications Center', desc: 'Consistent alerts across desktop + mobile PWA.', cat: 'comms', status: 'active' },
  { n: 76, title: 'Mobile Push Notifications', desc: 'To founder phone, with actionable buttons.', cat: 'comms', status: 'active' },
  { n: 77, title: 'On-Call Mode', desc: 'Escalations route to phone with persistent ringing until acknowledged.', cat: 'voice', status: 'active' },
  { n: 78, title: 'AI Escalation Summaries', desc: "When escalating, AI summarizes context so you don't re-read threads.", cat: 'ai', status: 'active' },
  { n: 79, title: 'Calendar-Aware Auto-Reply', desc: '"In a meeting; AI can help now; urgent? press 1."', cat: 'ai', status: 'active' },
  { n: 80, title: 'Communication SLAs by Plan', desc: 'Higher tiers get faster AI escalation or priority routing.', cat: 'compliance', status: 'configured' },
  { n: 81, title: 'Cross-Module Messaging', desc: "From denial dashboard, message the tenant's billing lead directly.", cat: 'comms', status: 'active' },
  { n: 82, title: 'Legal Hold Mode', desc: 'Freezes communication deletion for litigation risk.', cat: 'security', status: 'configured' },
  { n: 83, title: 'Conversation Compliance Labels', desc: 'Tags "CMS," "DEA," "Accreditation," "Billing" for audit.', cat: 'compliance', status: 'active' },
  { n: 84, title: 'Smart Draft Library', desc: 'Re-usable drafts; AI proposes best one.', cat: 'ai', status: 'active' },
  { n: 85, title: 'Voice Keyword Hot Alerts', desc: '"lawsuit," "audit," "fraud" triggers immediate founder alert.', cat: 'security', status: 'active' },
  { n: 86, title: 'Call Scheduling from Transcript', desc: '"Schedule follow-up" extracted and proposed.', cat: 'ai', status: 'active' },
  { n: 87, title: 'RCS Business Profile', desc: 'Verified brand, consistent display name.', cat: 'comms', status: 'configured' },
  { n: 88, title: 'Caller ID Management', desc: 'Consistent branded caller ID.', cat: 'comms', status: 'active' },
  { n: 89, title: 'Document Request Automation', desc: '"Missing PCS" triggers auto outreach + link.', cat: 'ai', status: 'active' },
  { n: 90, title: 'AI Phone System Training Notes', desc: 'You leave notes ("always ask for incident number first").', cat: 'ai', status: 'active' },
  { n: 91, title: 'Call Queue Dashboard', desc: 'Current callers, wait time, resolution probabilities.', cat: 'voice', status: 'active' },
  { n: 92, title: 'After-Hours AI Coverage', desc: 'AI handles and schedules tasks for morning.', cat: 'ai', status: 'active' },
  { n: 93, title: 'Inbound Routing by Region', desc: 'Wisconsin pilot rules vs other states.', cat: 'comms', status: 'configured' },
  { n: 94, title: 'Tenant Communications Heatmap', desc: 'Identify tenants needing attention.', cat: 'comms', status: 'active' },
  { n: 95, title: 'Global Search — All Channels', desc: 'Search across SMS/email/calls in one query.', cat: 'comms', status: 'active' },
  { n: 96, title: 'Escalation Throttling', desc: 'Prevents everything going to founder; AI bundles issues.', cat: 'ai', status: 'active' },
  { n: 97, title: 'Compliance Disclaimer Injector', desc: 'Adds required disclaimers automatically.', cat: 'compliance', status: 'active' },
  { n: 98, title: 'Billing Ticket Autolink', desc: 'Any billing comm ties to claim record.', cat: 'comms', status: 'active' },
  { n: 99, title: 'Smart Notifications Deduplication', desc: 'Combines related alerts.', cat: 'ai', status: 'active' },
  { n: 100, title: 'Founder One Pane of Glass', desc: "Single screen for today's priority: calls, denials, exports, invoices, compliance.", cat: 'comms', status: 'active' },
] as const;

type FilterCat = 'all' | 'comms' | 'ai' | 'security' | 'compliance' | 'voice';
type FilterStatus = 'all' | 'active' | 'configured' | 'pending';

export default function CommsInboxPage() {
  const [catFilter, setCatFilter] = useState<FilterCat>('all');
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [search, setSearch] = useState('');

  const filtered = COMM_MODULES.filter((m) => {
    if (catFilter !== 'all' && m.cat !== catFilter) return false;
    if (statusFilter !== 'all' && m.status !== statusFilter) return false;
    if (search && !m.title.toLowerCase().includes(search.toLowerCase()) && !m.desc.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const counts = {
    active: COMM_MODULES.filter((m) => m.status === 'active').length,
    configured: COMM_MODULES.filter((m) => m.status === 'configured').length,
    pending: COMM_MODULES.filter((m) => m.status === 'pending').length,
  };

  return (
    <div className="p-5 space-y-6 min-h-screen">
      <PageHeader
        title="Communications & Omnichannel Command"
        sub="100-item control surface — Unified Conversation Graph · AI Phone System · RCS/SMS/Voice/Video · SLA Enforcement"
        moduleRange="C1.1–100"
      />

      <KpiStrip items={[
        { label: 'Active Modules', value: `${counts.active}`, color: '#4caf50', trend: 'up' },
        { label: 'Configured', value: `${counts.configured}`, color: '#29b6f6' },
        { label: 'Pending', value: `${counts.pending}`, color: '#ff9800' },
        { label: 'Channels Live', value: '5', color: '#22d3ee' },
        { label: 'SLA Compliance', value: '96.4%', color: '#4caf50', trend: 'up' },
        { label: 'AI Handled', value: '83%', color: '#a855f7', trend: 'up' },
      ]} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)' }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,255,255,0.38)]">MODULE 18 · Priority Inbox</span>
            <span className="text-[9px] bg-[rgba(255,107,26,0.15)] text-[#ff6b1a] px-2 py-0.5 uppercase tracking-wider font-bold">AI-SORTED</span>
          </div>
          <ConversationThread from="Metro EMS — Chief Davis" channel="SMS" time="4m" preview="We're getting denial code 97 on all our Medicare transports this week — urgent" sentiment="negative" urgent={true} />
          <ConversationThread from="Valley Ambulance" channel="Voice" time="18m" preview="Called about NEMSIS export failure — transcript available" sentiment="neutral" urgent={false} />
          <ConversationThread from="Tri-County Fire" channel="RCS" time="42m" preview="PCS form attached — please confirm receipt and link to claim 2026-0441" sentiment="positive" urgent={false} />
          <ConversationThread from="City Hospital Billing" channel="Email" time="1h" preview="EOB received for batch 02/21 — 14 items need secondary billing" sentiment="neutral" urgent={false} />
          <ConversationThread from="State Compliance Office" channel="Fax" time="3h" preview="Audit packet request — response required within 5 business days" sentiment="negative" urgent={true} />
        </div>

        <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)' }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,255,255,0.38)]">MODULE 20 · SLA Enforcement Monitor</span>
            <span className="text-[9px] bg-[rgba(76,175,80,0.12)] text-[#4caf50] px-2 py-0.5 uppercase tracking-wider font-bold">MONITORING</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.05)]">
                {['Tenant', 'Channel', '1st Response', 'SLA Target', 'Status'].map((h) => (
                  <th key={h} className="text-left text-[9px] uppercase tracking-wider text-[rgba(255,255,255,0.3)] pb-2 pr-2 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <SLARow tenant="Metro EMS" channel="SMS" firstResponse="3m 12s" sla="< 5m" breached={false} />
              <SLARow tenant="Valley Amb." channel="Voice" firstResponse="AI (1m)" sla="< 2m" breached={false} />
              <SLARow tenant="Tri-County" channel="RCS" firstResponse="44m" sla="< 30m" breached={true} />
              <SLARow tenant="City Hosp." channel="Email" firstResponse="62m" sla="< 60m" breached={true} />
              <SLARow tenant="State Office" channel="Fax" firstResponse="Pending" sla="< 4h" breached={false} />
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
        <div className="text-[10px] font-bold uppercase tracking-widest text-[rgba(255,255,255,0.38)] mb-3">MODULE 46 · Communication Cost Monitor</div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { channel: 'Voice / AI', cost: '$0.018/min', volume: '342 min', total: '$6.16', color: '#22d3ee' },
            { channel: 'SMS', cost: '$0.0075/msg', volume: '1,204 msgs', total: '$9.03', color: '#4caf50' },
            { channel: 'RCS', cost: '$0.012/msg', volume: '286 msgs', total: '$3.43', color: '#a855f7' },
            { channel: 'Email', cost: '$0.001/msg', volume: '847 msgs', total: '$0.85', color: '#ff9800' },
            { channel: 'Fax', cost: '$0.05/pg', volume: '22 pgs', total: '$1.10', color: '#94a3b8' },
          ].map((c) => (
            <div key={c.channel} className="flex flex-col gap-0.5">
              <span className="text-[9px] uppercase tracking-wider font-semibold" style={{ color: c.color }}>{c.channel}</span>
              <span className="text-base font-bold text-white">{c.total}</span>
              <span className="text-[10px] text-[rgba(255,255,255,0.35)]">{c.volume}</span>
              <span className="text-[10px] text-[rgba(255,255,255,0.25)]">{c.cost}</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <span className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)]">FILTER:</span>
          <div className="flex gap-1 flex-wrap">
            {(['all', 'comms', 'ai', 'voice', 'compliance', 'security'] as FilterCat[]).map((f) => (
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
              category={m.cat as 'comms' | 'ai' | 'security' | 'compliance' | 'voice'}
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
      </div>
    </div>
  );
}
