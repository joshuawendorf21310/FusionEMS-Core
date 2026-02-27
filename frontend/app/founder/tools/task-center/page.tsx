'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE ?? '';

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="border-b border-[rgba(255,255,255,0.06)] pb-2 mb-4">
      <div className="flex items-baseline gap-3">
        <span className="text-[10px] font-bold text-[rgba(255,107,26,0.6)] font-mono">MODULE {number}</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-[rgba(255,255,255,0.85)]">{title}</h2>
        {sub && <span className="text-xs text-[rgba(255,255,255,0.35)]">{sub}</span>}
      </div>
    </div>
  );
}

function Badge({ label, status }: { label: string; status: 'ok' | 'warn' | 'error' | 'info' }) {
  const c = { ok: '#4caf50', warn: '#ff9800', error: '#e53935', info: '#29b6f6' };
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-semibold uppercase tracking-wider border"
      style={{ borderColor: `${c[status]}40`, color: c[status], background: `${c[status]}12` }}
    >
      <span className="w-1 h-1 rounded-full" style={{ background: c[status] }} />
      {label}
    </span>
  );
}

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4 ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

type TaskStatus = 'pending' | 'in-progress' | 'completed';
type TaskPriority = 'high' | 'medium' | 'low';

interface Task {
  id: number;
  task: string;
  category: string;
  due: string;
  priority: TaskPriority;
  status: TaskStatus;
  completed?: boolean;
}

const HIGH_PRIORITY_INIT: Task[] = [
  { id: 1, task: 'Review 3 denial appeals before 5PM', category: 'Revenue', due: 'Due Today', priority: 'high', status: 'pending' },
  { id: 2, task: 'Schedule Agency B onboarding call', category: 'Sales', due: 'Due Today', priority: 'high', status: 'pending' },
  { id: 3, task: 'Renew TX state API credentials', category: 'Compliance', due: 'Due Feb 7', priority: 'high', status: 'pending' },
  { id: 4, task: 'Review AI review queue (2 items)', category: 'AI', due: 'Due Today', priority: 'high', status: 'pending' },
];

const ALL_TASKS_INIT: Task[] = [
  { id: 5, task: 'Update onboarding documentation', category: 'Ops', due: 'Feb 3', priority: 'medium', status: 'in-progress' },
  { id: 6, task: 'Follow up Agency C contract renewal', category: 'Revenue', due: 'Feb 5', priority: 'medium', status: 'pending' },
  { id: 7, task: 'Review Q4 billing report', category: 'Billing', due: 'Feb 4', priority: 'medium', status: 'completed' },
  { id: 8, task: 'Test new NEMSIS export fields', category: 'Compliance', due: 'Feb 6', priority: 'high', status: 'in-progress' },
  { id: 9, task: 'Respond to Agency D support ticket', category: 'Support', due: 'Feb 2', priority: 'medium', status: 'pending' },
  { id: 10, task: 'Prepare Q1 investor deck', category: 'Executive', due: 'Feb 12', priority: 'medium', status: 'pending' },
  { id: 11, task: 'Archive Jan compliance documents', category: 'Compliance', due: 'Feb 5', priority: 'low', status: 'pending' },
  { id: 12, task: 'Audit user permission matrix', category: 'Security', due: 'Feb 10', priority: 'medium', status: 'pending' },
  { id: 13, task: 'Review SES bounce rate', category: 'Infra', due: 'Feb 3', priority: 'low', status: 'completed' },
  { id: 14, task: 'Update agency pricing page', category: 'Revenue', due: 'Feb 8', priority: 'medium', status: 'pending' },
  { id: 15, task: 'Set up new staging environment', category: 'Infra', due: 'Feb 9', priority: 'medium', status: 'in-progress' },
  { id: 16, task: 'Sign Agency F LOI', category: 'Sales', due: 'Feb 11', priority: 'medium', status: 'pending' },
  { id: 17, task: 'Review HIPAA BAA template changes', category: 'Legal', due: 'Feb 14', priority: 'medium', status: 'pending' },
  { id: 18, task: 'Finalize API rate limits policy', category: 'Infra', due: 'Feb 15', priority: 'low', status: 'pending' },
];

const COMPLETED_THIS_WEEK: Task[] = [
  { id: 101, task: 'Launched export retry fix', category: 'Infra', due: 'Jan 27', priority: 'high', status: 'completed' },
  { id: 102, task: 'Completed Agency A onboarding', category: 'Sales', due: 'Jan 26', priority: 'high', status: 'completed' },
  { id: 103, task: 'Submitted TX NEMSIS batch', category: 'Compliance', due: 'Jan 25', priority: 'high', status: 'completed' },
  { id: 104, task: 'Updated billing dashboard UI', category: 'Billing', due: 'Jan 25', priority: 'medium', status: 'completed' },
  { id: 105, task: 'Renewed SSL certificates', category: 'Infra', due: 'Jan 24', priority: 'medium', status: 'completed' },
  { id: 106, task: 'Reviewed AR aging report', category: 'Revenue', due: 'Jan 24', priority: 'medium', status: 'completed' },
  { id: 107, task: 'Closed Agency D renewal', category: 'Sales', due: 'Jan 23', priority: 'medium', status: 'completed' },
];

const DELEGATED = [
  { task: 'Implement export retry fix', assignee: 'Tech Lead', due: 'Feb 5', status: 'in-progress' as const },
  { task: 'Update NEMSIS field mappings', assignee: 'Compliance Specialist', due: 'Feb 8', status: 'pending' as const },
  { task: 'Design new onboarding flow', assignee: 'Designer', due: 'Feb 12', status: 'in-progress' as const },
];

const priorityStatus = (p: TaskPriority): 'ok' | 'warn' | 'error' | 'info' => {
  if (p === 'high') return 'error';
  if (p === 'medium') return 'warn';
  return 'info';
};

const taskStatusBadge = (s: TaskStatus) => {
  if (s === 'completed') return <Badge label="Completed" status="ok" />;
  if (s === 'in-progress') return <Badge label="In Progress" status="info" />;
  return <Badge label="Pending" status="warn" />;
};

export default function TaskCenterPage() {
  const [highTasks, setHighTasks] = useState<Task[]>(HIGH_PRIORITY_INIT);
  const [allTasks] = useState<Task[]>(ALL_TASKS_INIT);
  const [newTask, setNewTask] = useState({ task: '', due: '', category: 'Ops', priority: 'medium' as TaskPriority });

  function toggleHighTask(id: number) {
    setHighTasks((prev) =>
      prev.map((t) =>
        t.id === id ? { ...t, completed: !t.completed } : t
      )
    );
  }

  return (
    <div className="min-h-screen bg-[#080e16] text-white p-6 space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-bold text-[rgba(255,107,26,0.6)] font-mono tracking-widest uppercase">
            MODULE 11 · FOUNDER TOOLS
          </span>
          <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.4)] hover:text-[#ff6b1a] transition-colors">
            ← Back to Founder OS
          </Link>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white" style={{ textShadow: '0 0 24px rgba(255,107,26,0.3)' }}>
          Task Center
        </h1>
        <p className="text-xs text-[rgba(255,255,255,0.4)] mt-1">Founder action items · priorities · deadlines · team delegation</p>
      </motion.div>

      {/* MODULE 1 — Task Overview */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Total Tasks', value: '18', status: 'info' as const },
            { label: 'High Priority', value: '4', status: 'error' as const },
            { label: 'Due Today', value: '2', status: 'warn' as const },
            { label: 'Completed This Week', value: '7', status: 'ok' as const },
          ].map((s) => (
            <Panel key={s.label} className="flex flex-col gap-1">
              <span className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">{s.label}</span>
              <span
                className="text-2xl font-bold"
                style={{
                  color:
                    s.status === 'error'
                      ? '#e53935'
                      : s.status === 'warn'
                      ? '#ff9800'
                      : s.status === 'ok'
                      ? '#4caf50'
                      : 'rgba(255,255,255,0.9)',
                }}
              >
                {s.value}
              </span>
              <Badge label={s.label.split(' ')[0]} status={s.status} />
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 2 — High Priority Tasks */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Panel>
          <SectionHeader number="2" title="High Priority Tasks" sub="immediate action required" />
          <div className="space-y-2">
            {highTasks.map((t) => (
              <div
                key={t.id}
                className="flex items-center gap-3 p-2 rounded-sm transition-all"
                style={{
                  background: t.completed ? 'rgba(76,175,80,0.04)' : 'rgba(229,57,53,0.04)',
                  border: `1px solid ${t.completed ? 'rgba(76,175,80,0.15)' : 'rgba(229,57,53,0.15)'}`,
                }}
              >
                <button
                  onClick={() => toggleHighTask(t.id)}
                  className="w-4 h-4 rounded-sm border flex items-center justify-center shrink-0 transition-all"
                  style={{
                    borderColor: t.completed ? '#4caf50' : '#e53935',
                    background: t.completed ? 'rgba(76,175,80,0.2)' : 'transparent',
                  }}
                >
                  {t.completed && <span className="text-[10px] text-[#4caf50] font-bold leading-none">&#10003;</span>}
                </button>
                <span
                  className="flex-1 text-xs"
                  style={{
                    color: t.completed ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.8)',
                    textDecoration: t.completed ? 'line-through' : 'none',
                  }}
                >
                  {t.task}
                </span>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] text-[rgba(255,255,255,0.35)] font-mono">{t.due}</span>
                  <Badge label={t.category} status="info" />
                  <span className="w-2 h-2 rounded-full" style={{ background: '#e53935' }} />
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 3 — All Tasks */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <Panel>
          <SectionHeader number="3" title="All Tasks" sub="14 additional items" />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.06)]">
                  {['#', 'Task', 'Category', 'Due', 'Priority', 'Status'].map((h) => (
                    <th key={h} className="text-left py-1.5 px-2 text-[rgba(255,255,255,0.35)] font-semibold uppercase tracking-wider text-[10px]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {allTasks.map((t, i) => (
                  <tr key={t.id} className="border-b border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.02)]">
                    <td className="py-1.5 px-2 font-mono text-[rgba(255,107,26,0.6)] text-[11px]">{i + 1}</td>
                    <td
                      className="py-1.5 px-2"
                      style={{
                        color: t.status === 'completed' ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.75)',
                        textDecoration: t.status === 'completed' ? 'line-through' : 'none',
                      }}
                    >
                      {t.task}
                    </td>
                    <td className="py-1.5 px-2 text-[rgba(255,255,255,0.45)]">{t.category}</td>
                    <td className="py-1.5 px-2 font-mono text-[rgba(255,255,255,0.45)] text-[11px]">{t.due}</td>
                    <td className="py-1.5 px-2">
                      <Badge label={t.priority} status={priorityStatus(t.priority)} />
                    </td>
                    <td className="py-1.5 px-2">{taskStatusBadge(t.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 4 — Add Task */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Panel>
          <SectionHeader number="4" title="Add Task" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="flex flex-col gap-1 lg:col-span-2">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Task Description</label>
              <input
                type="text"
                value={newTask.task}
                onChange={(e) => setNewTask({ ...newTask, task: e.target.value })}
                placeholder="Describe the task..."
                className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a] placeholder:text-[rgba(255,255,255,0.2)]"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Due Date</label>
              <input
                type="date"
                value={newTask.due}
                onChange={(e) => setNewTask({ ...newTask, due: e.target.value })}
                className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a]"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Category</label>
              <select
                value={newTask.category}
                onChange={(e) => setNewTask({ ...newTask, category: e.target.value })}
                className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a]"
              >
                {['Ops', 'Sales', 'Compliance', 'Billing', 'Revenue', 'Infra', 'Legal', 'Executive', 'AI', 'Security', 'Support'].map((c) => (
                  <option key={c} value={c} className="bg-[#0f1720]">{c}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-[rgba(255,255,255,0.4)] uppercase tracking-wider">Priority</label>
              <select
                value={newTask.priority}
                onChange={(e) => setNewTask({ ...newTask, priority: e.target.value as TaskPriority })}
                className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] text-xs text-white px-3 py-2 rounded-sm outline-none focus:border-[#ff6b1a]"
              >
                {(['high', 'medium', 'low'] as TaskPriority[]).map((p) => (
                  <option key={p} value={p} className="bg-[#0f1720]">{p}</option>
                ))}
              </select>
            </div>
            <div className="flex items-end lg:col-span-1">
              <button
                className="px-4 py-2 text-xs font-bold uppercase tracking-widest rounded-sm transition-all hover:brightness-110"
                style={{ background: '#ff6b1a', color: '#000' }}
                onClick={() => setNewTask({ task: '', due: '', category: 'Ops', priority: 'medium' })}
              >
                Add Task
              </button>
            </div>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 5 — Completed This Week */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <Panel>
          <SectionHeader number="5" title="Completed This Week" sub="7 tasks" />
          <div className="space-y-2">
            {COMPLETED_THIS_WEEK.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between py-2 border-b border-[rgba(255,255,255,0.04)] last:border-0"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[#4caf50] font-bold text-sm">&#10003;</span>
                  <span className="text-xs line-through text-[rgba(255,255,255,0.3)]">{t.task}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-2">
                  <span className="text-[10px] font-mono text-[rgba(255,255,255,0.25)]">{t.due}</span>
                  <Badge label={t.category} status="ok" />
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 6 — Delegated Tasks */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
        <Panel>
          <SectionHeader number="6" title="Delegated Tasks" sub="team assignments" />
          <div className="space-y-3">
            {DELEGATED.map((d, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 rounded-sm"
                style={{
                  background: d.status === 'in-progress' ? 'rgba(41,182,246,0.04)' : 'rgba(255,152,0,0.04)',
                  border: `1px solid ${d.status === 'in-progress' ? 'rgba(41,182,246,0.15)' : 'rgba(255,152,0,0.15)'}`,
                }}
              >
                <div>
                  <p className="text-xs font-semibold text-[rgba(255,255,255,0.8)]">{d.task}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-[rgba(255,255,255,0.4)]">→</span>
                    <span className="text-[10px] text-[rgba(255,107,26,0.8)] font-semibold">{d.assignee}</span>
                    <span className="text-[10px] text-[rgba(255,255,255,0.3)]">·</span>
                    <span className="text-[10px] font-mono text-[rgba(255,255,255,0.35)]">Due {d.due}</span>
                  </div>
                </div>
                <Badge
                  label={d.status === 'in-progress' ? 'In Progress' : 'Pending'}
                  status={d.status === 'in-progress' ? 'info' : 'warn'}
                />
              </div>
            ))}
          </div>
        </Panel>
      </motion.div>

      <div className="pt-2">
        <Link href="/founder" className="text-[11px] text-[rgba(255,255,255,0.35)] hover:text-[#ff6b1a] transition-colors">
          ← Back to Founder OS
        </Link>
      </div>
    </div>
  );
}
