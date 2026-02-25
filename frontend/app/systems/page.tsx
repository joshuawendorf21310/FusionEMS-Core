import { api } from "../../components/api";
import Link from "next/link";
import { StatusBadge, SystemStatus } from "../../components/AppShell";

type SystemRow = { system_key: string; name: string; description: string; status: SystemStatus; accent?: string };

export default async function SystemsPage() {
  const systems = await api<SystemRow[]>("/api/v1/systems");
  return (
    <div className="space-y-4">
      <div className="text-lg font-semibold">Systems</div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {systems.map(s => (
          <Link key={s.system_key} href={`/systems/${s.system_key}`} className="rounded-2xl border border-border bg-panel p-5 hover:bg-[rgba(255,255,255,0.04)]">
            <div className="text-sm font-semibold">{s.name}</div>
            <div className="mt-1 text-xs text-muted">{s.description}</div>
            <div className="mt-3">
              <StatusBadge status={s.status} accent={s.accent ?? "#94a3b8"} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
