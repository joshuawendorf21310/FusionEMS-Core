'use client';
import { useState, useEffect, useCallback, useRef } from 'react';

interface Scenario {
  id: string;
  data: {
    name: string;
    summary: string;
    dataset_type: string;
    expected_result: string;
    sections: string[];
  };
}

interface RunResult {
  passed: boolean;
  issue_count: number;
  message?: string;
}

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [runResults, setRunResults] = useState<Record<string, RunResult>>({});
  const [runningId, setRunningId] = useState<string | null>(null);
  const uploadRef = useRef<HTMLInputElement>(null);

  const fetchScenarios = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/nemsis/studio/scenarios', { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setScenarios(Array.isArray(data) ? data : (data.scenarios ?? []));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploadStatus('Uploading...');
    const form = new FormData();
    form.append('file', files[0]);
    try {
      const res = await fetch('/api/v1/nemsis/studio/scenarios/upload', {
        method: 'POST',
        credentials: 'include',
        body: form,
      });
      if (res.ok) {
        setUploadStatus(`Uploaded: ${files[0].name}`);
        fetchScenarios();
      } else {
        setUploadStatus(`Error: ${res.status}`);
      }
    } catch (e: unknown) {
      setUploadStatus(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const runScenario = async (id: string) => {
    setRunningId(id);
    try {
      const res = await fetch(`/api/v1/nemsis/studio/scenarios/${id}/run`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data = await res.json();
        setRunResults((prev) => ({ ...prev, [id]: { passed: data.passed, issue_count: data.issue_count ?? 0, message: data.message } }));
      } else {
        setRunResults((prev) => ({ ...prev, [id]: { passed: false, issue_count: 0, message: `HTTP ${res.status}` } }));
      }
    } catch (e: unknown) {
      setRunResults((prev) => ({ ...prev, [id]: { passed: false, issue_count: 0, message: e instanceof Error ? e.message : String(e) } }));
    } finally {
      setRunningId(null);
    }
  };

  return (
    <div className="p-5 space-y-6 min-h-screen bg-[#090e14]">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(34,211,238,0.6)] mb-1">
          ePCR · TEST SCENARIOS
        </div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">Test Scenarios</h1>
        <p className="text-xs text-[rgba(255,255,255,0.38)] mt-0.5">C&amp;S vendor test case browser and runner</p>
      </div>

      <div className="flex items-center gap-3">
        <input
          ref={uploadRef}
          type="file"
          accept=".xml,.zip,.json"
          className="hidden"
          onChange={(e) => handleUpload(e.target.files)}
        />
        <button
          onClick={() => uploadRef.current?.click()}
          className="bg-[#0f1720] border border-[rgba(34,211,238,0.3)] text-[#22d3ee] text-xs px-4 py-2 hover:bg-[rgba(34,211,238,0.08)] transition-colors"
        >
          Upload Scenario File
        </button>
        {uploadStatus && <span className="text-xs text-[rgba(255,255,255,0.5)]">{uploadStatus}</span>}
      </div>

      {loading ? (
        <div className="text-xs text-[rgba(255,255,255,0.3)]">Loading scenarios...</div>
      ) : scenarios.length === 0 ? (
        <div className="text-xs text-[rgba(255,255,255,0.3)]">No scenarios uploaded yet</div>
      ) : (
        <div className="space-y-3">
          {scenarios.map((scenario) => {
            const d = scenario.data || {};
            const result = runResults[scenario.id];
            const isRunning = runningId === scenario.id;
            return (
              <div
                key={scenario.id}
                className="bg-[#0f1720] border border-[rgba(255,255,255,0.08)] p-4 space-y-3"
                style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-bold text-white">{d.name || 'Untitled Scenario'}</div>
                    {d.summary && (
                      <div className="text-xs text-[rgba(255,255,255,0.45)] mt-0.5">{d.summary}</div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 ${d.dataset_type === 'DEM' ? 'bg-purple-900 text-purple-300' : 'bg-blue-900 text-blue-300'}`}
                    >
                      {d.dataset_type || 'EMS'}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 ${d.expected_result === 'PASS' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}
                    >
                      Expected: {d.expected_result || 'PASS'}
                    </span>
                  </div>
                </div>

                {d.sections && d.sections.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {d.sections.map((s: string, i: number) => (
                      <span key={i} className="text-[10px] bg-[#0a1018] border border-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.5)] px-2 py-0.5">
                        {s}
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => runScenario(scenario.id)}
                    disabled={isRunning}
                    className="text-xs bg-[#22d3ee] text-[#090e14] font-bold px-4 py-1.5 hover:bg-[#06b6d4] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    {isRunning ? (
                      <span className="flex items-center gap-1.5">
                        <span className="inline-block w-3 h-3 border-2 border-[#090e14] border-t-transparent rounded-full animate-spin" />
                        Running...
                      </span>
                    ) : (
                      'Run'
                    )}
                  </button>
                  {result && (
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 ${result.passed ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}
                      >
                        {result.passed ? 'PASS' : 'FAIL'}
                      </span>
                      <span className="text-xs text-[rgba(255,255,255,0.4)]">
                        {result.issue_count} issue{result.issue_count !== 1 ? 's' : ''}
                      </span>
                      {result.message && (
                        <span className="text-xs text-[rgba(255,255,255,0.35)]">{result.message}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="pt-2">
        <a href="/founder/epcr" className="text-xs text-[rgba(34,211,238,0.6)] hover:text-[#22d3ee]">
          ← Back to ePCR
        </a>
      </div>
    </div>
  );
}
