'use client';
import { QuantumTableSkeleton, QuantumCardSkeleton } from '@/components/ui';
import { useState, useEffect, useCallback } from 'react';

type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'rejected';

interface PatchTask {
  id: string;
  data: {
    title: string;
    element_id: string;
    fix_type: string;
    description: string;
    steps: string[];
    status: TaskStatus;
  };
}

const FIX_TYPE_COLORS: Record<string, string> = {
  exporter_bug: 'bg-red-900 text-red-300',
  mapping_bug: 'bg-orange-900 text-orange-300',
  ui_rule: 'bg-blue-900 text-blue-300',
  code_list: 'bg-purple-900 text-purple-300',
  schema_rule: 'bg-yellow-900 text-yellow-300',
  config: 'bg-teal-900 text-teal-300',
};

const COLUMNS: { key: TaskStatus; label: string }[] = [
  { key: 'pending', label: 'Pending' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'completed', label: 'Completed' },
  { key: 'rejected', label: 'Rejected' },
];

export default function PatchTasksPage() {
  const [tasks, setTasks] = useState<PatchTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/nemsis/studio/patch-tasks', { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setTasks(Array.isArray(data) ? data : (data.tasks ?? []));
      }
    } catch (e: unknown) {
      console.warn('[patch-tasks fetch error]', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const updateStatus = async (id: string, newStatus: TaskStatus) => {
    setUpdatingId(id);
    try {
      const res = await fetch(`/api/v1/nemsis/studio/patch-tasks/${id}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        setTasks((prev) =>
          prev.map((t) =>
            t.id === id ? { ...t, data: { ...t.data, status: newStatus } } : t
          )
        );
      }
    } catch (e: unknown) {
      console.warn('[patch-task update error]', e);
    } finally {
      setUpdatingId(null);
    }
  };

  const columnTasks = (colKey: TaskStatus) =>
    tasks.filter((t) => (t.data?.status ?? 'pending') === colKey);

  if (loading) {
    return (
      <div className="p-5 min-h-screen bg-bg-void flex items-center">
        <span className="text-xs text-[rgba(255,255,255,0.3)]">Loading patch tasks...</span>
      </div>
    );
  }

  return (
    <div className="p-5 space-y-6 min-h-screen bg-bg-void">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(34,211,238,0.6)] mb-1">
          ePCR · PATCH TASKS
        </div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Patch Tasks</h1>
        <p className="text-xs text-text-muted mt-0.5">
          AI-generated fix tasks from validation issues
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {COLUMNS.map((col) => {
          const colTasks = columnTasks(col.key);
          return (
            <div key={col.key} className="flex flex-col gap-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold uppercase tracking-wider text-[rgba(255,255,255,0.5)]">
                  {col.label}
                </span>
                <span className="text-[10px] bg-bg-input border border-border-DEFAULT text-[rgba(255,255,255,0.4)] px-2 py-0.5">
                  {colTasks.length}
                </span>
              </div>
              <div className="space-y-2 min-h-[120px]">
                {colTasks.length === 0 && (
                  <div className="text-[11px] text-[rgba(255,255,255,0.2)] italic pt-2">No tasks</div>
                )}
                {colTasks.map((task) => {
                  const d = task.data || {};
                  const fixTypeClass = FIX_TYPE_COLORS[d.fix_type] ?? 'bg-bg-raised text-text-secondary';
                  const isUpdating = updatingId === task.id;
                  const nextStatuses = COLUMNS.filter((c) => c.key !== col.key).map((c) => c.key);
                  return (
                    <div
                      key={task.id}
                      className="bg-bg-panel border border-border-DEFAULT p-3 space-y-2"
                      style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
                    >
                      <div className="text-xs font-bold text-text-primary leading-tight">{d.title || 'Untitled Task'}</div>
                      <div className="flex flex-wrap items-center gap-1.5">
                        {d.element_id && (
                          <span className="text-[10px] font-mono text-system-billing">{d.element_id}</span>
                        )}
                        {d.fix_type && (
                          <span className={`text-[10px] font-bold px-2 py-0.5 ${fixTypeClass}`}>
                            {d.fix_type}
                          </span>
                        )}
                      </div>
                      {d.description && (
                        <p className="text-[11px] text-[rgba(255,255,255,0.45)] leading-tight">
                          {d.description.length > 100 ? `${d.description.slice(0, 100)}...` : d.description}
                        </p>
                      )}
                      {d.steps && d.steps.length > 0 && (
                        <div className="text-[10px] text-[rgba(255,255,255,0.3)]">
                          {d.steps.length} step{d.steps.length !== 1 ? 's' : ''}
                        </div>
                      )}
                      <div className="flex flex-wrap gap-1 pt-1">
                        {nextStatuses.map((ns) => (
                          <button
                            key={ns}
                            onClick={() => updateStatus(task.id, ns)}
                            disabled={isUpdating}
                            className="text-[10px] bg-bg-input border border-[rgba(255,255,255,0.12)] text-[rgba(255,255,255,0.5)] px-2 py-0.5 hover:border-[rgba(34,211,238,0.3)] hover:text-system-billing disabled:opacity-40 transition-colors"
                          >
                            → {ns.replace('_', ' ')}
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div className="pt-2">
        <a href="/founder/epcr" className="text-xs text-[rgba(34,211,238,0.6)] hover:text-system-billing">
          ← Back to ePCR
        </a>
      </div>
    </div>
  );
}
