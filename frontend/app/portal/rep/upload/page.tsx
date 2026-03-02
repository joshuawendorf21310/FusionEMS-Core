'use client';

import { useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';

const PANEL_STYLE = {
  clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
  background: 'var(--color-bg-panel, var(--color-bg-input))',
  border: '1px solid rgba(255,255,255,0.08)',
};

const BTN_PRIMARY: React.CSSProperties = {
  clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
  background: 'var(--color-brand-orange)',
  color: 'var(--color-text-primary)',
  fontWeight: 600,
  fontSize: '0.9375rem',
  padding: '11px 24px',
  border: 'none',
  cursor: 'pointer',
  letterSpacing: '0.02em',
};

const LABEL_STYLE: React.CSSProperties = {
  display: 'block',
  fontSize: '0.75rem',
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: 'rgba(255,255,255,0.5)',
  marginBottom: '6px',
};

const DOC_TYPES = [
  {
    key: 'power_of_attorney',
    label: 'Power of Attorney',
    desc: 'A signed legal document granting you authority to act on behalf of the patient.',
  },
  {
    key: 'healthcare_proxy',
    label: 'Healthcare Proxy',
    desc: 'Designates you as the agent to make healthcare decisions for the patient.',
  },
  {
    key: 'legal_guardianship',
    label: 'Legal Guardianship Order',
    desc: 'A court order establishing your legal guardianship of the patient.',
  },
  {
    key: 'court_authorization',
    label: 'Court Authorization Letter',
    desc: 'A court-issued letter authorizing you to manage the patient\'s affairs.',
  },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function RepUploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const ACCEPTED = ['application/pdf', 'image/jpeg', 'image/png'];
  const MAX_BYTES = 10 * 1024 * 1024;

  function validateAndSet(file: File) {
    if (!ACCEPTED.includes(file.type)) {
      setError('Unsupported file type. Please upload a PDF, JPG, or PNG.');
      return;
    }
    if (file.size > MAX_BYTES) {
      setError('File exceeds the 10 MB limit.');
      return;
    }
    setError('');
    setSelectedFile(file);
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) validateAndSet(file);
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) validateAndSet(file);
  }, []);

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragging(true);
  }

  function handleDragLeave() {
    setDragging(false);
  }

  async function handleUpload() {
    if (!selectedFile || !docType) {
      setError('Please select a file and document type.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const token = sessionStorage.getItem('rep_token') ?? '';
      const sessionId = sessionStorage.getItem('rep_session_id') ?? '';
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('document_type', docType);
      formData.append('session_id', sessionId);

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/auth-rep/documents`,
        {
          method: 'POST',
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: formData,
        }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `Upload failed (${res.status})`);
      }
      router.push('/portal/rep/sign');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{ background: 'var(--color-bg-base, var(--color-bg-base))', minHeight: '100vh' }}
      className="flex items-center justify-center px-4 py-12"
    >
      <div style={{ width: '100%', maxWidth: '560px' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '48px',
              height: '48px',
              background: 'rgba(255,107,26,0.12)',
              border: '1px solid rgba(255,107,26,0.3)',
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
              marginBottom: '18px',
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-orange)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <h1 style={{ color: 'var(--color-text-primary)', fontSize: '1.375rem', fontWeight: 700, margin: '0 0 8px' }}>
            Upload Authorization Documents
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.875rem', margin: 0 }}>
            Upload a signed Power of Attorney, Legal Guardianship Order, or other authorization document
          </p>
        </div>

        {/* Card */}
        <div style={{ ...PANEL_STYLE, padding: '28px' }}>
          {/* Document type selector */}
          <div style={{ marginBottom: '22px' }}>
            <label style={LABEL_STYLE} htmlFor="doc-type">Document Type</label>
            <select
              id="doc-type"
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              style={{
                width: '100%',
                background: 'var(--color-bg-input)',
                border: '1px solid rgba(255,255,255,0.08)',
                clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
                color: docType ? 'var(--color-text-primary)' : 'rgba(255,255,255,0.3)',
                fontSize: '0.9375rem',
                padding: '10px 12px',
                outline: 'none',
                appearance: 'none',
                cursor: 'pointer',
              }}
              disabled={loading}
            >
              <option value="" disabled>Select document type...</option>
              {DOC_TYPES.map((d) => (
                <option key={d.key} value={d.key}>{d.label}</option>
              ))}
            </select>
          </div>

          {/* Drop zone */}
          <div
            onClick={() => !loading && fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            style={{
              border: `2px dashed ${dragging ? 'rgba(255,107,26,0.6)' : 'rgba(255,255,255,0.12)'}`,
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
              background: dragging ? 'rgba(255,107,26,0.05)' : 'rgba(255,255,255,0.02)',
              padding: '40px 24px',
              textAlign: 'center',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'border-color 0.15s, background 0.15s',
              marginBottom: '20px',
            }}
          >
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 12px' }}>
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: '0.9375rem', margin: '0 0 4px', fontWeight: 500 }}>
              Click to upload or drag and drop
            </p>
            <p style={{ color: 'rgba(255,255,255,0.28)', fontSize: '0.8125rem', margin: 0 }}>
              PDF, JPG, PNG up to 10MB
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={handleFileInput}
              style={{ display: 'none' }}
              disabled={loading}
            />
          </div>

          {/* File preview */}
          {selectedFile && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 14px',
                background: 'rgba(255,107,26,0.07)',
                border: '1px solid rgba(255,107,26,0.2)',
                clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)',
                marginBottom: '20px',
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-orange)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ color: 'var(--color-text-primary)', fontSize: '0.875rem', margin: '0 0 2px', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {selectedFile.name}
                </p>
                <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', margin: 0 }}>
                  {formatBytes(selectedFile.size)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => { setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                disabled={loading}
                style={{
                  background: 'none',
                  border: '1px solid rgba(255,255,255,0.12)',
                  clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
                  color: 'rgba(255,255,255,0.5)',
                  fontSize: '0.75rem',
                  padding: '4px 10px',
                  cursor: 'pointer',
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                }}
              >
                Remove
              </button>
            </div>
          )}

          {error && (
            <div
              style={{
                background: 'rgba(220,38,38,0.12)',
                border: '1px solid rgba(220,38,38,0.35)',
                clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
                color: 'var(--color-brand-red)',
                fontSize: '0.8125rem',
                padding: '10px 12px',
                marginBottom: '16px',
              }}
            >
              {error}
            </div>
          )}

          <button
            type="button"
            onClick={handleUpload}
            disabled={!selectedFile || !docType || loading}
            style={{
              ...BTN_PRIMARY,
              width: '100%',
              padding: '11px 0',
              opacity: !selectedFile || !docType || loading ? 0.4 : 1,
              cursor: !selectedFile || !docType || loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Uploading...' : 'Upload & Continue'}
          </button>
        </div>

        {/* Accepted document types */}
        <div style={{ ...PANEL_STYLE, padding: '20px 24px', marginTop: '16px' }}>
          <p style={{ ...LABEL_STYLE, marginBottom: '14px' }}>Accepted Document Types</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {DOC_TYPES.map((d) => (
              <div key={d.key} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                <div
                  style={{
                    width: '6px',
                    height: '6px',
                    background: 'var(--color-brand-orange)',
                    borderRadius: '50%',
                    marginTop: '6px',
                    flexShrink: 0,
                  }}
                />
                <div>
                  <p style={{ color: 'rgba(255,255,255,0.75)', fontSize: '0.875rem', margin: '0 0 2px', fontWeight: 500 }}>
                    {d.label}
                  </p>
                  <p style={{ color: 'rgba(255,255,255,0.35)', fontSize: '0.8125rem', margin: 0 }}>
                    {d.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
