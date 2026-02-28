'use client';

import { useState, useRef, useEffect } from 'react';
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

const AGREEMENT_TEXT = `I, the undersigned Authorized Representative, hereby authorize FusionEMS, Inc. and its designated billing service providers, third-party processors, and collections partners (collectively, "FusionEMS") to discuss, disclose, review, and resolve all billing matters, insurance claims, and account balances related to the patient account specified in my registration on my behalf. This authorization includes, but is not limited to, the right to receive billing statements, negotiate payment arrangements, dispute claims, access Explanation of Benefits (EOB) documents, and communicate with insurance carriers regarding covered services.

I attest that I am legally authorized to act on behalf of the patient named in my registration by virtue of my relationship as described therein, including but not limited to spousal authority, parental authority, legal guardianship, healthcare proxy designation, or duly executed Power of Attorney. I understand that providing false or misleading information in connection with this authorization may constitute fraud and may be subject to civil and/or criminal penalties under applicable state and federal law.

I acknowledge that FusionEMS is entitled to rely on this authorization until such time as it receives written notice of revocation. I may revoke this authorization at any time by submitting a written request to the FusionEMS Compliance Department. Revocation will not affect actions taken by FusionEMS in good faith prior to its receipt of the revocation notice.

By signing below, I confirm that I have read and understood the foregoing authorization, that all information I have provided is true and accurate to the best of my knowledge, and that I consent to the electronic storage of my signature as a legally binding representation of my agreement to these terms.`;

export default function RepSignPage() {
  const router = useRouter();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [drawing, setDrawing] = useState(false);
  const [hasSig, setHasSig] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const lastPos = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.fillStyle = 'var(--color-bg-input)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }, []);

  function getPos(e: React.MouseEvent | React.TouchEvent, canvas: HTMLCanvasElement) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    if ('touches' in e) {
      const t = e.touches[0];
      return { x: (t.clientX - rect.left) * scaleX, y: (t.clientY - rect.top) * scaleY };
    }
    return { x: ((e as React.MouseEvent).clientX - rect.left) * scaleX, y: ((e as React.MouseEvent).clientY - rect.top) * scaleY };
  }

  function startDraw(e: React.MouseEvent | React.TouchEvent) {
    e.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) return;
    setDrawing(true);
    lastPos.current = getPos(e, canvas);
  }

  function draw(e: React.MouseEvent | React.TouchEvent) {
    e.preventDefault();
    if (!drawing) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx || !lastPos.current) return;
    const pos = getPos(e, canvas);
    ctx.beginPath();
    ctx.moveTo(lastPos.current.x, lastPos.current.y);
    ctx.lineTo(pos.x, pos.y);
    ctx.strokeStyle = 'var(--color-text-primary)';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();
    lastPos.current = pos;
    setHasSig(true);
  }

  function endDraw(e: React.MouseEvent | React.TouchEvent) {
    e.preventDefault();
    setDrawing(false);
    lastPos.current = null;
  }

  function clearCanvas() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.fillStyle = 'var(--color-bg-input)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    setHasSig(false);
  }

  async function handleSubmit() {
    if (!agreed || !hasSig) return;
    setError('');
    setLoading(true);
    try {
      const canvas = canvasRef.current;
      const sigDataUrl = canvas ? canvas.toDataURL('image/png') : '';
      const token = sessionStorage.getItem('rep_token') ?? '';
      const repId = sessionStorage.getItem('rep_id') ?? '';

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/auth-rep/sign`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            authorized_rep_id: repId,
            signature_data: sigDataUrl,
            agreed_to_terms: true,
          }),
        }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `Submission failed (${res.status})`);
      }
      router.push('/portal/patient');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = agreed && hasSig && !loading;

  return (
    <div
      style={{ background: 'var(--color-bg-base, #0b0f14)', minHeight: '100vh' }}
      className="flex items-center justify-center px-4 py-12"
    >
      <div style={{ width: '100%', maxWidth: '600px' }}>
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
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
          </div>
          <h1 style={{ color: 'var(--color-text-primary)', fontSize: '1.375rem', fontWeight: 700, margin: '0 0 8px' }}>
            Sign Authorization Agreement
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.875rem', margin: 0 }}>
            Review and sign the authorization agreement below
          </p>
        </div>

        {/* Agreement text */}
        <div
          style={{
            ...PANEL_STYLE,
            padding: '20px 22px',
            marginBottom: '16px',
          }}
        >
          <p
            style={{
              fontSize: '0.75rem',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'rgba(255,255,255,0.4)',
              marginBottom: '12px',
            }}
          >
            Authorization Agreement
          </p>
          <div
            style={{
              maxHeight: '300px',
              overflowY: 'auto',
              paddingRight: '8px',
              scrollbarWidth: 'thin',
              scrollbarColor: 'rgba(255,255,255,0.12) transparent',
            }}
          >
            {AGREEMENT_TEXT.split('\n\n').map((para, i) => (
              <p
                key={i}
                style={{
                  color: 'rgba(255,255,255,0.65)',
                  fontSize: '0.875rem',
                  lineHeight: 1.7,
                  margin: i === 0 ? '0 0 14px' : '14px 0',
                }}
              >
                {para}
              </p>
            ))}
          </div>
        </div>

        {/* Signature canvas */}
        <div style={{ ...PANEL_STYLE, padding: '20px 22px', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <p
              style={{
                fontSize: '0.75rem',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: 'rgba(255,255,255,0.4)',
                margin: 0,
              }}
            >
              Signature
            </p>
            <button
              type="button"
              onClick={clearCanvas}
              style={{
                background: 'none',
                border: '1px solid rgba(255,255,255,0.12)',
                clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
                color: 'rgba(255,255,255,0.45)',
                fontSize: '0.75rem',
                padding: '4px 12px',
                cursor: 'pointer',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}
            >
              Clear
            </button>
          </div>

          <div
            style={{
              position: 'relative',
              border: `2px dashed ${hasSig ? 'rgba(255,107,26,0.4)' : 'rgba(255,255,255,0.1)'}`,
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
              overflow: 'hidden',
            }}
          >
            {!hasSig && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  pointerEvents: 'none',
                  zIndex: 1,
                }}
              >
                <span style={{ color: 'rgba(255,255,255,0.18)', fontSize: '1rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  Sign Here
                </span>
              </div>
            )}
            <canvas
              ref={canvasRef}
              width={556}
              height={140}
              style={{ display: 'block', width: '100%', height: '140px', cursor: 'crosshair', touchAction: 'none' }}
              onMouseDown={startDraw}
              onMouseMove={draw}
              onMouseUp={endDraw}
              onMouseLeave={endDraw}
              onTouchStart={startDraw}
              onTouchMove={draw}
              onTouchEnd={endDraw}
            />
          </div>
        </div>

        {/* Checkbox */}
        <div
          style={{
            ...PANEL_STYLE,
            padding: '16px 20px',
            marginBottom: '16px',
            cursor: 'pointer',
          }}
          onClick={() => setAgreed((v) => !v)}
        >
          <label style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', cursor: 'pointer' }}>
            <div
              style={{
                width: '18px',
                height: '18px',
                border: `1px solid ${agreed ? 'var(--color-brand-orange)' : 'rgba(255,255,255,0.2)'}`,
                background: agreed ? 'var(--color-brand-orange)' : 'transparent',
                clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)',
                flexShrink: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginTop: '1px',
              }}
            >
              {agreed && (
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-primary)" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
            </div>
            <span style={{ color: 'rgba(255,255,255,0.65)', fontSize: '0.875rem', lineHeight: 1.5 }}>
              I agree to the terms above and confirm my identity as the authorized representative for this patient account
            </span>
          </label>
        </div>

        {error && (
          <div
            style={{
              background: 'rgba(220,38,38,0.12)',
              border: '1px solid rgba(220,38,38,0.35)',
              clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
              color: '#f87171',
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
          onClick={handleSubmit}
          disabled={!canSubmit}
          style={{
            ...BTN_PRIMARY,
            width: '100%',
            padding: '13px 0',
            opacity: canSubmit ? 1 : 0.35,
            cursor: canSubmit ? 'pointer' : 'not-allowed',
          }}
        >
          {loading ? 'Submitting...' : 'Submit Signature'}
        </button>
      </div>
    </div>
  );
}
