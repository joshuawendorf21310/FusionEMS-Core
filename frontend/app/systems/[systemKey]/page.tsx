"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ModalContainer, SystemStatus } from "../../../components/AppShell";

type SystemRow = { system_key: string; name: string; description: string; status: SystemStatus; accent?: string };

const CAD_MODAL = "FusionCAD is architecturally defined within the Quantum infrastructure roadmap and will activate in alignment with multi-agency deployment strategy.";
const DEFAULT_GATE_MODAL = "This system has completed architectural development and is pending regulatory certification before live deployment.";

export default function SystemPage() {
  const { systemKey } = useParams<{ systemKey: string }>();
  const router = useRouter();
  const [system, setSystem] = useState<SystemRow | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    (async () => {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || "http://localhost:8000";
      const res = await fetch(`${base}/api/v1/systems`, { cache: "no-store" });
      const systems = (await res.json()) as SystemRow[];
      const s = systems.find(x => x.system_key === systemKey) || null;
      setSystem(s);
      if (s && s.status !== "ACTIVE") setOpen(true);
    })().catch(() => setOpen(true));
  }, [systemKey]);

  const modalBody = useMemo(() => {
    if (systemKey === "fusioncad") return CAD_MODAL;
    return DEFAULT_GATE_MODAL;
  }, [systemKey]);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-panel p-6">
        <div className="text-lg font-semibold">{system?.name ?? String(systemKey)}</div>
        <div className="mt-2 text-sm text-muted">{system?.description ?? "System page."}</div>
        <div className="mt-4 text-xs text-muted">This page is certification-gated unless system status is ACTIVE.</div>
      </div>

      <ModalContainer
        open={open}
        title={systemKey === "fusioncad" ? "Infrastructure Layer" : "Certification Activation Required"}
        body={modalBody}
        onClose={() => { setOpen(false); router.push("/systems"); }}
        ctaLabel="Return to Architecture"
      />
    </div>
  );
}
