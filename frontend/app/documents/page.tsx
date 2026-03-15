"use client";

import { useState } from "react";

type DocType = "patient_report" | "claim_packet" | "compliance_summary" | "export_confirmation";

interface DocumentTemplate {
  id: DocType;
  label: string;
  description: string;
  category: string;
}

const TEMPLATES: DocumentTemplate[] = [
  {
    id: "patient_report",
    label: "Patient Care Report",
    description: "Printable patient care report with incident details, vitals, and interventions. Print-safe layout with agency branding.",
    category: "Operations",
  },
  {
    id: "claim_packet",
    label: "Claim Packet",
    description: "Billing claim packet including transport details, insurance information, and supporting documentation for submission.",
    category: "Billing",
  },
  {
    id: "compliance_summary",
    label: "Compliance Summary",
    description: "NEMSIS compliance summary with validation status, requisite elements, and audit trail for regulatory review.",
    category: "Compliance",
  },
  {
    id: "export_confirmation",
    label: "Export Confirmation",
    description: "Confirmation document for data exports including timestamps, record counts, and validation results.",
    category: "Operations",
  },
];

function TemplateCard({
  template,
  onGenerate,
}: {
  template: DocumentTemplate;
  onGenerate: (id: DocType) => void;
}) {
  return (
    <div
      className="chamfer-8 border p-5 flex flex-col gap-3"
      style={{
        backgroundColor: "var(--color-bg-panel)",
        borderColor: "var(--color-border-default)",
      }}
    >
      <div className="flex items-center justify-between">
        <span
          style={{
            fontFamily: "var(--font-label)",
            fontSize: "var(--text-body)",
            fontWeight: 700,
            color: "var(--color-text-primary)",
          }}
        >
          {template.label}
        </span>
        <span
          className="label-caps px-2 py-0.5 chamfer-4"
          style={{
            fontSize: "var(--text-micro)",
            color: "var(--color-brand-orange)",
            backgroundColor: "rgba(255,106,0,0.08)",
            border: "1px solid rgba(255,106,0,0.2)",
          }}
        >
          {template.category}
        </span>
      </div>
      <p style={{ fontSize: "var(--text-body)", color: "var(--color-text-muted)", lineHeight: 1.5 }}>
        {template.description}
      </p>
      <button
        onClick={() => onGenerate(template.id)}
        className="chamfer-4 mt-auto self-start px-4 py-2 text-sm font-semibold transition-colors"
        style={{
          backgroundColor: "var(--color-brand-orange)",
          color: "var(--color-text-inverse)",
        }}
      >
        Generate PDF
      </button>
    </div>
  );
}

export default function DocumentsPage() {
  const [generating, setGenerating] = useState<DocType | null>(null);
  const [message, setMessage] = useState("");

  function handleGenerate(id: DocType) {
    setGenerating(id);
    setMessage("");
    // Simulate generation — in production, calls backend PDF endpoint
    setTimeout(() => {
      setGenerating(null);
      setMessage(`Document generated: ${TEMPLATES.find((t) => t.id === id)?.label}. Ready for download.`);
    }, 1500);
  }

  return (
    <div className="min-h-screen px-6 py-8" style={{ backgroundColor: "var(--color-bg-void)" }}>
      <div className="mx-auto max-w-5xl space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-3">
            <div
              className="chamfer-4 flex h-8 w-8 items-center justify-center"
              style={{
                backgroundColor: "var(--color-brand-orange)",
                color: "var(--color-text-inverse)",
                fontWeight: 700,
                fontSize: "var(--text-label)",
              }}
            >
              FQ
            </div>
            <h1
              style={{
                fontFamily: "var(--font-label)",
                fontSize: "var(--text-h2)",
                fontWeight: 700,
                color: "var(--color-text-primary)",
                letterSpacing: "0.02em",
              }}
            >
              Documents &amp; Printing
            </h1>
          </div>
          <p className="mt-1" style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
            Enterprise document generation — print-safe, branded, audit-ready
          </p>
        </div>

        {/* Capabilities */}
        <div
          className="chamfer-8 border px-5 py-4"
          style={{
            backgroundColor: "var(--color-bg-panel)",
            borderColor: "var(--color-border-default)",
          }}
        >
          <span className="label-caps" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-label)" }}>
            System Capabilities
          </span>
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
            {["HTML-to-PDF Generation", "Agency Branding", "Print-Safe Layout", "Export / Download"].map(
              (cap) => (
                <div
                  key={cap}
                  className="chamfer-4 flex items-center gap-2 px-3 py-2 border"
                  style={{
                    borderColor: "var(--color-border-subtle)",
                    fontSize: "var(--text-micro)",
                    color: "var(--color-text-primary)",
                  }}
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: "var(--color-status-active)" }}
                  />
                  {cap}
                </div>
              )
            )}
          </div>
        </div>

        {/* Status message */}
        {generating && (
          <div
            className="chamfer-8 flex items-center gap-3 px-5 py-3 border animate-pulse"
            style={{
              borderColor: "var(--color-brand-orange)",
              backgroundColor: "var(--color-bg-panel)",
              color: "var(--color-brand-orange)",
              fontSize: "var(--text-body)",
            }}
          >
            Generating document…
          </div>
        )}
        {message && (
          <div
            className="chamfer-8 flex items-center gap-3 px-5 py-3 border"
            style={{
              borderColor: "var(--color-status-active)",
              backgroundColor: "var(--color-bg-panel)",
              color: "var(--color-status-active)",
              fontSize: "var(--text-body)",
            }}
          >
            {message}
          </div>
        )}

        {/* Templates */}
        <div>
          <span className="label-caps" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-label)" }}>
            Document Templates
          </span>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4">
            {TEMPLATES.map((t) => (
              <TemplateCard key={t.id} template={t} onGenerate={handleGenerate} />
            ))}
          </div>
        </div>

        <div className="text-center pt-2">
          <span style={{ fontSize: "var(--text-micro)", color: "var(--color-text-muted)" }}>
            FusionEMS Quantum Documents — Professional, print-safe, enterprise-grade
          </span>
        </div>
      </div>
    </div>
  );
}
