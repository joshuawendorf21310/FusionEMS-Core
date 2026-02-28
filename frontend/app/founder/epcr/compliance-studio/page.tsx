'use client';
import { QuantumTableSkeleton, QuantumCardSkeleton } from '@/components/ui';
import { useState, useEffect, useCallback, useRef } from 'react';

interface PackStatus {
  national_xsd: { active: boolean; name: string } | null;
  wi_schematron: { active: boolean; name: string } | null;
  wi_state_dataset: { active: boolean; name: string } | null;
}

interface ValidationIssue {
  severity: string;
  element_id: string;
  ui_section: string;
  rule_source: string;
  plain_message: string;
  fix_hint: string;
}

interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
  record_id?: string;
}

interface AiExplanation {
  plain_explanation: string;
  fix_type: string;
  patch_task: { steps: string[] };
}

interface CertCheck {
  label: string;
  passed: boolean;
}

export default function ComplianceStudioPage() {
  const [packStatus, setPackStatus] = useState<PackStatus | null>(null);
  const [packLoading, setPackLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [isDragging, setIsDragging] = useState(false);
  const [validationFile, setValidationFile] = useState<File | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [aiExplanations, setAiExplanations] = useState<Record<number, AiExplanation | null>>({});
  const [aiLoadingIdx, setAiLoadingIdx] = useState<number | null>(null);
  const [certChecks, setCertChecks] = useState<CertCheck[]>([]);
  const [certLoading, setCertLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropFileInputRef = useRef<HTMLInputElement>(null);

  const fetchPackStatus = useCallback(async () => {
    setPackLoading(true);
    try {
      const res = await fetch('/api/v1/nemsis/packs?active=true', { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        const packs: { data: { pack_type?: string; pack_name?: string; active?: boolean } }[] = Array.isArray(data) ? data : [];
        const national = packs.find((p) => p.data?.pack_type === 'national_xsd');
        const wi_sch = packs.find((p) => p.data?.pack_type === 'wi_schematron');
        const wi_ds = packs.find((p) => p.data?.pack_type === 'wi_state_dataset');
        setPackStatus({
          national_xsd: national ? { active: !!national.data?.active, name: national.data?.pack_name || 'National XSD' } : null,
          wi_schematron: wi_sch ? { active: !!wi_sch.data?.active, name: wi_sch.data?.pack_name || 'WI Schematron' } : null,
          wi_state_dataset: wi_ds ? { active: !!wi_ds.data?.active, name: wi_ds.data?.pack_name || 'WI State Dataset' } : null,
        });
      }
    } catch {
      setPackStatus({ national_xsd: null, wi_schematron: null, wi_state_dataset: null });
    } finally {
      setPackLoading(false);
    }
  }, []);

  const fetchCertChecks = useCallback(async () => {
    setCertLoading(true);
    try {
      const res = await fetch('/api/v1/nemsis/studio/certification-checklist', { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setCertChecks(Array.isArray(data.checks) ? data.checks : []);
      }
    } catch {
      setCertChecks([]);
    } finally {
      setCertLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPackStatus();
    fetchCertChecks();
  }, [fetchPackStatus, fetchCertChecks]);

  const handleDropFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploadStatus('Creating pack...');
    const file = files[0];
    const form = new FormData();
    form.append('file', file);
    form.append('pack_name', file.name);
    try {
      const res = await fetch('/api/v1/nemsis/packs', {
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({ pack_name: file.name, pack_type: 'upload' }),
        headers: { 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        const rec = await res.json();
        const packId = rec?.id || rec?.data?.pack_id || 'new';
        const uploadForm = new FormData();
        uploadForm.append('file', file);
        const uploadRes = await fetch(`/api/v1/nemsis/packs/${packId}/files/upload`, {
          method: 'POST',
          credentials: 'include',
          body: uploadForm,
        });
        if (uploadRes.ok) {
          setUploadStatus(`Uploaded: ${file.name}`);
          fetchPackStatus();
        } else {
          setUploadStatus(`Pack created (id=${packId}), file upload returned ${uploadRes.status}`);
        }
      } else {
        setUploadStatus(`Error: ${res.status} ${res.statusText}`);
      }
    } catch (e: unknown) {
      setUploadStatus(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, [fetchPackStatus]);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleDropFiles(e.dataTransfer.files);
  };

  const runValidation = async () => {
    if (!validationFile) return;
    setValidationLoading(true);
    setValidationResult(null);
    setAiExplanations({});
    const form = new FormData();
    form.append('file', validationFile);
    try {
      const res = await fetch('/api/v1/nemsis/studio/validate-file', {
        method: 'POST',
        credentials: 'include',
        body: form,
      });
      if (res.ok) {
        const data = await res.json();
        setValidationResult(data);
      } else {
        setValidationResult({ valid: false, issues: [{ severity: 'error', element_id: 'request', ui_section: '', rule_source: '', plain_message: `Server error: ${res.status}`, fix_hint: '' }] });
      }
    } catch (e: unknown) {
      setValidationResult({ valid: false, issues: [{ severity: 'error', element_id: 'network', ui_section: '', rule_source: '', plain_message: e instanceof Error ? e.message : String(e), fix_hint: '' }] });
    } finally {
      setValidationLoading(false);
    }
  };

  const fetchAiExplain = async (idx: number) => {
    if (!validationResult?.record_id) return;
    setAiLoadingIdx(idx);
    try {
      const res = await fetch('/api/v1/nemsis/studio/ai-explain', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ validation_result_id: validationResult.record_id, issue_index: idx }),
      });
      if (res.ok) {
        const data = await res.json();
        setAiExplanations((prev) => ({ ...prev, [idx]: data }));
      }
    } finally {
      setAiLoadingIdx(null);
    }
  };

  const sendAllToAgent = async () => {
    if (!validationResult?.record_id) return;
    try {
      await fetch('/api/v1/nemsis/studio/patch-tasks/generate-from-result', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ validation_result_id: validationResult.record_id }),
      });
    } catch (err: unknown) {
      console.warn("[compliance-studio]", err);
    }
  };

  const errorCount = validationResult?.issues.filter((i) => i.severity === 'error').length ?? 0;
  const warnCount = validationResult?.issues.filter((i) => i.severity === 'warning').length ?? 0;

  return (
    <div className="p-5 space-y-6 min-h-screen bg-bg-void">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(34,211,238,0.6)] mb-1">
          ePCR · COMPLIANCE STUDIO
        </div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Compliance Studio</h1>
        <p className="text-xs text-text-muted mt-0.5">
          Turn-key visual certification — resource packs, validation, AI fix list
        </p>
      </div>

      <div className="bg-bg-panel border border-border-DEFAULT p-4 space-y-2">
        <div className="text-xs font-bold uppercase tracking-wider text-[rgba(255,255,255,0.5)] mb-3">Pack Status</div>
        {packLoading ? (
          <div className="p-6"><QuantumTableSkeleton rows={6} cols={4} /></div>
        ) : (
          <div className="flex flex-wrap gap-3">
            {[
              { key: 'national_xsd', label: 'National XSD' },
              { key: 'wi_schematron', label: 'WI Schematron' },
              { key: 'wi_state_dataset', label: 'WI State Dataset' },
            ].map(({ key, label }) => {
              const pack = packStatus?.[key as keyof PackStatus];
              return (
                <div key={key} className="flex items-center gap-2 bg-bg-input border border-border-DEFAULT px-3 py-2">
                  <span
                    className={`inline-block w-2 h-2 rounded-full ${pack?.active ? 'bg-green-400' : 'bg-red-500'}`}
                  />
                  <span className="text-xs text-text-primary">{pack?.name || label}</span>
                  <span className={`text-[10px] font-bold ${pack?.active ? 'text-green-400' : 'text-red-400'}`}>
                    {pack?.active ? 'Active' : 'Missing'}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div
        className={`border-2 border-dashed rounded transition-colors ${isDragging ? 'border-cyan-400 bg-bg-input' : 'border-border-strong bg-bg-panel'} p-8 text-center`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <div className="text-[rgba(255,255,255,0.5)] text-sm mb-2">
          Drop NEMSIS resource files here (XSD, Schematron, StateDataSet, ZIP)
        </div>
        <div className="text-[rgba(255,255,255,0.3)] text-xs mb-4">or click to browse</div>
        <input
          ref={dropFileInputRef}
          type="file"
          accept=".xsd,.sch,.xml,.zip"
          className="hidden"
          onChange={(e) => handleDropFiles(e.target.files)}
        />
        <button
          onClick={() => dropFileInputRef.current?.click()}
          className="bg-bg-input border border-[rgba(34,211,238,0.3)] text-system-billing text-xs px-4 py-2 hover:bg-[rgba(34,211,238,0.08)] transition-colors"
        >
          Browse Files
        </button>
        {uploadStatus && (
          <div className="mt-3 text-xs text-[rgba(255,255,255,0.6)]">{uploadStatus}</div>
        )}
      </div>

      <div className="bg-bg-panel border border-border-DEFAULT p-4 space-y-3">
        <div className="text-xs font-bold uppercase tracking-wider text-[rgba(255,255,255,0.5)]">Validate XML File</div>
        <div className="flex items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xml"
            className="hidden"
            onChange={(e) => setValidationFile(e.target.files?.[0] ?? null)}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="bg-bg-input border border-border-strong text-[rgba(255,255,255,0.6)] text-xs px-3 py-2 hover:border-[rgba(255,255,255,0.3)] transition-colors"
          >
            {validationFile ? validationFile.name : 'Choose XML file'}
          </button>
          <button
            onClick={runValidation}
            disabled={!validationFile || validationLoading}
            className="bg-system-billing text-text-inverse text-xs font-bold px-5 py-2 hover:bg-system-billing disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {validationLoading ? (
              <span className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 border-2 border-bg-void border-t-transparent rounded-full animate-spin" />
                Running...
              </span>
            ) : (
              'Run Validation'
            )}
          </button>
        </div>
      </div>

      {validationResult && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span
                className={`text-xs font-bold px-2 py-1 ${validationResult.valid ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}
              >
                {validationResult.valid ? 'VALID' : 'INVALID'}
              </span>
              <span className="text-xs text-red-400">{errorCount} error{errorCount !== 1 ? 's' : ''}</span>
              <span className="text-xs text-yellow-400">{warnCount} warning{warnCount !== 1 ? 's' : ''}</span>
            </div>
            <button
              onClick={sendAllToAgent}
              className="text-xs bg-bg-panel border border-[rgba(34,211,238,0.3)] text-system-billing px-3 py-1.5 hover:bg-[rgba(34,211,238,0.08)] transition-colors"
            >
              Send All to Agent
            </button>
          </div>

          <div className="space-y-2">
            {validationResult.issues.map((issue, idx) => (
              <div
                key={idx}
                className="bg-bg-panel border border-border-DEFAULT p-4 space-y-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 uppercase ${issue.severity === 'error' ? 'bg-red-900 text-red-300' : 'bg-yellow-900 text-yellow-300'}`}
                  >
                    {issue.severity}
                  </span>
                  <span className="text-xs font-mono text-system-billing">{issue.element_id}</span>
                  {issue.ui_section && (
                    <span className="text-[10px] text-[rgba(255,255,255,0.4)]">{issue.ui_section}</span>
                  )}
                  {issue.rule_source && (
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 ${issue.rule_source.toLowerCase().includes('wisconsin') ? 'bg-blue-900 text-blue-300' : 'bg-bg-raised text-text-secondary'}`}
                    >
                      {issue.rule_source}
                    </span>
                  )}
                </div>
                <p className="text-xs text-[rgba(255,255,255,0.75)]">{issue.plain_message}</p>
                {issue.fix_hint && (
                  <p className="text-[11px] text-[rgba(255,255,255,0.4)] italic">{issue.fix_hint}</p>
                )}
                <div>
                  <button
                    onClick={() => fetchAiExplain(idx)}
                    disabled={aiLoadingIdx === idx}
                    className="text-[11px] text-system-billing hover:underline disabled:opacity-40"
                  >
                    {aiLoadingIdx === idx ? 'Loading...' : 'AI Explain'}
                  </button>
                </div>
                {aiExplanations[idx] && (
                  <div className="mt-2 bg-bg-input border border-[rgba(34,211,238,0.15)] p-3 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold text-system-billing">AI EXPLANATION</span>
                      <span className="text-[10px] bg-purple-900 text-purple-300 px-2 py-0.5 font-bold">
                        {aiExplanations[idx]!.fix_type}
                      </span>
                    </div>
                    <p className="text-xs text-[rgba(255,255,255,0.7)]">{aiExplanations[idx]!.plain_explanation}</p>
                    {aiExplanations[idx]!.patch_task?.steps?.length > 0 && (
                      <div>
                        <div className="text-[10px] text-[rgba(255,255,255,0.4)] mb-1 uppercase tracking-wider">Steps</div>
                        <ol className="space-y-1 list-decimal list-inside">
                          {aiExplanations[idx]!.patch_task.steps.map((step, si) => (
                            <li key={si} className="text-[11px] text-text-secondary">{step}</li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-bg-panel border border-border-DEFAULT p-4">
        <div className="text-xs font-bold uppercase tracking-wider text-[rgba(255,255,255,0.5)] mb-3">
          Certification Checklist
        </div>
        {certLoading ? (
          <div className="p-6"><QuantumTableSkeleton rows={6} cols={4} /></div>
        ) : certChecks.length === 0 ? (
          <div className="text-xs text-[rgba(255,255,255,0.3)]">No checklist data available</div>
        ) : (
          <div className="space-y-1.5">
            {certChecks.map((check, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className={`text-sm ${check.passed ? 'text-green-400' : 'text-red-400'}`}>
                  {check.passed ? '✓' : '✗'}
                </span>
                <span className="text-xs text-text-secondary">{check.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="pt-2">
        <a href="/founder/epcr" className="text-xs text-[rgba(34,211,238,0.6)] hover:text-system-billing">
          ← Back to ePCR
        </a>
      </div>
    </div>
  );
}
