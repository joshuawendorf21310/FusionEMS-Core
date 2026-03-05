import { api } from "../../components/api";
import Link from "next/link";
import { StatusBadge, SystemStatus } from "../../components/AppShell";

type SystemRow = { system_key: string; name: string; description: string; status: SystemStatus; accent?: string };

export default async function SystemsPage() {
  let systems: SystemRow[] = [];
  try {
    systems = await api<SystemRow[]>("/api/v1/systems");
  } catch {
    systems = [
      { system_key:"fusionbilling", name:"FusionBilling", description:"Revenue & claims engine", status:"ACTIVE", accent:"var(--color-status-info)" },
      { system_key:"fusionems", name:"FusionEMS", description:"Clinical documentation engine", status:"CERTIFICATION_ACTIVATION_REQUIRED", accent:"var(--color-brand-orange-bright)" },
      { system_key:"fusionfire", name:"FusionFire", description:"Fire reporting engine", status:"CERTIFICATION_ACTIVATION_REQUIRED", accent:"var(--color-brand-red)" },
      { system_key:"fusionhems", name:"FusionHEMS", description:"Air medical operations engine", status:"ARCHITECTURE_COMPLETE", accent:"var(--color-status-warning)" },
      { system_key:"fusioncompliance", name:"FusionCompliance", description:"Compliance & audit layer", status:"ACTIVE_CORE_LAYER", accent:"var(--color-system-compliance)" },
      { system_key:"fusionai", name:"FusionAI", description:"Governed AI co-pilot layer", status:"ACTIVE_CORE_LAYER", accent:"var(--color-text-primary)" },
      { system_key:"fusionfleet", name:"FusionFleet", description:"Fleet readiness engine", status:"IN_DEVELOPMENT", accent:"var(--color-system-fleet)" },
      { system_key:"fusioncad", name:"FusionCAD", description:"CAD & incident coordination engine", status:"INFRASTRUCTURE_LAYER", accent:"var(--color-text-muted)" },
    ];
  }
  return (
    <div className="space-y-4">
      <div className="text-lg font-semibold">Systems</div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {systems.map(s => (
          <Link key={s.system_key} href={`/systems/${s.system_key}`} className="rounded-2xl border border-border bg-panel p-5 hover:bg-[rgba(255,255,255,0.04)]">
            <div className="text-sm font-semibold">{s.name}</div>
            <div className="mt-1 text-xs text-muted">{s.description}</div>
            <div className="mt-3">
              <StatusBadge status={s.status} accent={s.accent ?? "var(--color-text-muted)"} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
