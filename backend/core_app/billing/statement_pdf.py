from __future__ import annotations

import hashlib
import io
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

try:
    from reportlab.lib import colors  # noqa: F401
    from reportlab.lib.pagesizes import letter as LETTER_SIZE  # noqa: F401
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: F401
    from reportlab.lib.units import inch, mm  # noqa: F401
    from reportlab.pdfgen import canvas as rl_canvas  # noqa: F401
    from reportlab.platypus import (  # noqa: F401
        BaseDocTemplate,
        Frame,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

TEMPLATE_VERSION = "v1.0.0"

# ── Brand tokens ─────────────────────────────────────────────────────────────
_C = colors.HexColor if REPORTLAB_AVAILABLE else None

CHARCOAL      = _C("#1a1f2e") if REPORTLAB_AVAILABLE else None
CHARCOAL_MID  = _C("#252b3d") if REPORTLAB_AVAILABLE else None
CHARCOAL_LITE = _C("#343d56") if REPORTLAB_AVAILABLE else None
ORANGE        = _C("#f97316") if REPORTLAB_AVAILABLE else None
ORANGE_DARK   = _C("#c2601a") if REPORTLAB_AVAILABLE else None
RED_CRITICAL  = _C("#dc2626") if REPORTLAB_AVAILABLE else None
OFF_WHITE     = _C("#f1f5f9") if REPORTLAB_AVAILABLE else None
TICK_GREY     = _C("#4b5563") if REPORTLAB_AVAILABLE else None
WHITE         = colors.white if REPORTLAB_AVAILABLE else None

# Address window safe-zone (Lob window spec): x=0.75in, y=2.00in from bottom-left, w=4.0in, h=1.0in
LOB_WINDOW_X      = 0.75 * inch if REPORTLAB_AVAILABLE else 0
LOB_WINDOW_Y      = 2.00 * inch if REPORTLAB_AVAILABLE else 0
LOB_WINDOW_W      = 4.00 * inch if REPORTLAB_AVAILABLE else 0
LOB_WINDOW_H      = 1.00 * inch if REPORTLAB_AVAILABLE else 0
LOB_WINDOW_MARGIN = 0.10 * inch if REPORTLAB_AVAILABLE else 0

PAGE_W, PAGE_H = (8.5 * inch, 11 * inch) if REPORTLAB_AVAILABLE else (0, 0)


@dataclass
class StatementContext:
    statement_id: str
    tenant_id: str
    patient_name: str
    patient_address: dict[str, str]
    agency_name: str
    agency_address: dict[str, str]
    agency_phone: str
    incident_date: str
    transport_date: str
    service_lines: list[dict[str, Any]]
    amount_due_cents: int
    amount_paid_cents: int
    pay_url: str
    generated_at: datetime | None = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now(UTC)


def _require_reportlab() -> None:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab not installed: pip install reportlab")


# ── Low-level drawing helpers ─────────────────────────────────────────────────

def _hud_ticks(c: Any, x: float, y: float, w: float, gap: float = 8.0, length: float = 4.0) -> None:
    c.setStrokeColor(TICK_GREY)
    c.setLineWidth(0.5)
    nx = int(w / gap)
    for i in range(nx + 1):
        tx = x + i * gap
        c.line(tx, y, tx, y + length)


def _chamfer_rect(
    c: Any, x: float, y: float, w: float, h: float,
    cut: float = 6.0, fill_color: Any = None, stroke_color: Any = None
) -> None:
    p = c.beginPath()
    p.moveTo(x + cut, y)
    p.lineTo(x + w - cut, y)
    p.lineTo(x + w, y + cut)
    p.lineTo(x + w, y + h - cut)
    p.lineTo(x + w - cut, y + h)
    p.lineTo(x + cut, y + h)
    p.lineTo(x, y + h - cut)
    p.lineTo(x, y + cut)
    p.close()
    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(1.0)
    if fill_color and stroke_color:
        c.drawPath(p, fill=1, stroke=1)
    elif fill_color:
        c.drawPath(p, fill=1, stroke=0)
    else:
        c.drawPath(p, fill=0, stroke=1)


def _angled_separator(c: Any, x: float, y: float, w: float, angle_deg: float = 30.0) -> None:
    rise = math.tan(math.radians(angle_deg)) * 12
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1.2)
    c.line(x, y, x + w, y + rise)


def _audit_footer(c: Any, ctx: StatementContext, pdf_hash: str, page_num: int) -> None:
    footer_y = 0.35 * inch
    c.setFillColor(TICK_GREY)
    c.setFont("Courier", 5.5)
    line = (
        f"STMT:{ctx.statement_id}  TID:{ctx.tenant_id}  "
        f"TPL:{TEMPLATE_VERSION}  GEN:{ctx.generated_at.strftime('%Y-%m-%dT%H:%M:%SZ')}  "
        f"SHA256:{pdf_hash[:16]}…  PG:{page_num}"
    )
    c.drawString(0.5 * inch, footer_y, line)
    c.setStrokeColor(TICK_GREY)
    c.setLineWidth(0.25)
    c.line(0.5 * inch, footer_y + 7, PAGE_W - 0.5 * inch, footer_y + 7)


def _header_plate(c: Any, agency_name: str) -> None:
    plate_h = 0.90 * inch
    plate_y = PAGE_H - plate_h - 0.30 * inch
    _chamfer_rect(c, 0.45 * inch, plate_y, PAGE_W - 0.90 * inch, plate_h,
                  cut=8.0, fill_color=CHARCOAL, stroke_color=CHARCOAL_LITE)
    _hud_ticks(c, 0.50 * inch, plate_y + plate_h - 6, PAGE_W - 1.00 * inch, gap=10.0, length=4.0)
    _angled_separator(c, 0.45 * inch, plate_y + plate_h * 0.40, PAGE_W - 0.90 * inch)

    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(0.65 * inch, plate_y + plate_h * 0.62, "FusionEMS QUANTUM")

    c.setFillColor(OFF_WHITE)
    c.setFont("Helvetica", 8)
    c.drawString(0.65 * inch, plate_y + plate_h * 0.30, agency_name.upper())

    c.setFillColor(ORANGE_DARK)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawRightString(PAGE_W - 0.65 * inch, plate_y + plate_h * 0.62, "MEDICAL TRANSPORT BILLING STATEMENT")
    c.setFillColor(TICK_GREY)
    c.setFont("Courier", 6)
    c.drawRightString(PAGE_W - 0.65 * inch, plate_y + plate_h * 0.30, "CONFIDENTIAL — HIPAA PROTECTED")


# ── Page 1 builder ─────────────────────────────────────────────────────────────

def _build_page1(c: Any, ctx: StatementContext, pdf_hash: str) -> None:
    c.setPageSize((PAGE_W, PAGE_H))

    # Background
    c.setFillColor(OFF_WHITE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Header
    _header_plate(c, ctx.agency_name)

    # ── Address window safe-zone (Lob spec) ──────────────────────────────────
    # Lob requires page 1 address block at 0.75–4.75in x, 2.0–3.0in y (from bottom)
    # We leave the zone completely CLEAR of graphics and only print the address text
    win_x = LOB_WINDOW_X
    win_y = LOB_WINDOW_Y
    win_h = LOB_WINDOW_H

    # Recipient address inside window
    addr = ctx.patient_address
    c.setFillColor(CHARCOAL)
    c.setFont("Helvetica", 8)
    lines = [
        ctx.patient_name,
        addr.get("line1", ""),
        addr.get("line2", ""),
        f"{addr.get('city', '')}, {addr.get('state', '')} {addr.get('zip', '')}",
    ]
    text_y = win_y + win_h - LOB_WINDOW_MARGIN - 9
    for ln in lines:
        if ln.strip():
            c.drawString(win_x + LOB_WINDOW_MARGIN, text_y, ln)
            text_y -= 10

    # From / return address (top-left above window area)
    from_y = win_y + win_h + 0.18 * inch
    c.setFillColor(CHARCOAL)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(win_x, from_y + 10, ctx.agency_name)
    c.setFont("Helvetica", 7.5)
    fa = ctx.agency_address
    c.drawString(win_x, from_y, fa.get("line1", ""))
    c.drawString(win_x, from_y - 10,
                 f"{fa.get('city', '')}, {fa.get('state', '')} {fa.get('zip', '')}  {ctx.agency_phone}")

    # ── Statement details panel (right column) ───────────────────────────────
    det_x = 5.20 * inch
    det_y = PAGE_H - 1.45 * inch
    det_w = PAGE_W - det_x - 0.45 * inch

    _chamfer_rect(c, det_x, det_y - 1.10 * inch, det_w, 1.10 * inch,
                  cut=5.0, fill_color=CHARCOAL_MID, stroke_color=CHARCOAL_LITE)

    labels = [
        ("Statement ID",   ctx.statement_id[:18] + "…" if len(ctx.statement_id) > 18 else ctx.statement_id),
        ("Incident Date",  ctx.incident_date),
        ("Transport Date", ctx.transport_date),
        ("Due Date",       (ctx.generated_at + __import__("datetime").timedelta(days=30)).strftime("%m/%d/%Y")),
    ]
    row_y = det_y - 0.18 * inch
    for label, val in labels:
        c.setFillColor(TICK_GREY)
        c.setFont("Helvetica", 6.5)
        c.drawString(det_x + 0.10 * inch, row_y, label.upper())
        c.setFillColor(OFF_WHITE)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(det_x + 0.10 * inch, row_y - 8, val)
        row_y -= 22

    # ── Service lines table ──────────────────────────────────────────────────
    tbl_x = 0.45 * inch
    tbl_y = 3.50 * inch
    tbl_w = PAGE_W - 0.90 * inch

    section_h = 0.22 * inch
    _chamfer_rect(c, tbl_x, tbl_y + section_h, tbl_w, section_h,
                  cut=4.0, fill_color=CHARCOAL, stroke_color=None)
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(tbl_x + 0.10 * inch, tbl_y + section_h + 4, "SERVICES RENDERED")

    col_widths = [0.70 * inch, 0.55 * inch, 2.80 * inch, 0.60 * inch, 0.70 * inch, 0.70 * inch, 0.70 * inch]
    headers = ["DATE", "CODE", "DESCRIPTION", "QTY", "RATE", "BILLED", "ALLOWED"]

    row_h = 0.17 * inch
    cur_y = tbl_y - row_h * 0.1

    # Table header row
    _chamfer_rect(c, tbl_x, cur_y - row_h, tbl_w, row_h,
                  cut=3.0, fill_color=CHARCOAL_MID, stroke_color=None)
    rx = tbl_x + 0.05 * inch
    c.setFillColor(OFF_WHITE)
    c.setFont("Helvetica-Bold", 6.5)
    for i, hdr in enumerate(headers):
        c.drawString(rx, cur_y - row_h + 4, hdr)
        rx += col_widths[i]
    cur_y -= row_h

    # Data rows
    for idx, svc in enumerate(ctx.service_lines):
        bg = CHARCOAL_LITE if idx % 2 == 0 else CHARCOAL_MID
        c.setFillColor(bg)
        c.rect(tbl_x, cur_y - row_h, tbl_w, row_h, fill=1, stroke=0)
        rx = tbl_x + 0.05 * inch
        c.setFillColor(OFF_WHITE)
        c.setFont("Helvetica", 6.5)
        vals = [
            svc.get("date", ""),
            svc.get("code", ""),
            svc.get("description", ""),
            str(svc.get("qty", 1)),
            f"${svc.get('rate_cents', 0)/100:,.2f}",
            f"${svc.get('billed_cents', 0)/100:,.2f}",
            f"${svc.get('allowed_cents', 0)/100:,.2f}",
        ]
        for i, val in enumerate(vals):
            c.drawString(rx, cur_y - row_h + 4, str(val)[:28])
            rx += col_widths[i]
        cur_y -= row_h

    # ── Balance summary plate ────────────────────────────────────────────────
    bal_y = 0.75 * inch
    bal_x = PAGE_W - 2.60 * inch
    bal_w = 2.10 * inch
    bal_h = 0.90 * inch

    total_due = ctx.amount_due_cents / 100
    is_critical = ctx.amount_due_cents > 0

    plate_color = RED_CRITICAL if is_critical else CHARCOAL_MID
    _chamfer_rect(c, bal_x, bal_y, bal_w, bal_h,
                  cut=7.0, fill_color=plate_color, stroke_color=ORANGE)
    c.setFillColor(OFF_WHITE)
    c.setFont("Helvetica", 7)
    c.drawCentredString(bal_x + bal_w / 2, bal_y + bal_h - 0.16 * inch, "AMOUNT DUE")
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(bal_x + bal_w / 2, bal_y + 0.35 * inch, f"${total_due:,.2f}")
    c.setFont("Helvetica", 6)
    c.setFillColor(ORANGE)
    c.drawCentredString(bal_x + bal_w / 2, bal_y + 0.15 * inch, "PAY ONLINE OR BY PHONE")

    # Pay URL
    c.setFillColor(CHARCOAL)
    c.setFont("Helvetica", 7)
    c.drawString(0.50 * inch, bal_y + 0.35 * inch, "Pay online:")
    c.setFillColor(ORANGE)
    c.setFont("Courier", 6.5)
    c.drawString(0.50 * inch, bal_y + 0.22 * inch, ctx.pay_url[:70])

    # HUD ticks bottom strip
    _hud_ticks(c, 0.45 * inch, 0.60 * inch, PAGE_W - 0.90 * inch, gap=12.0, length=5.0)

    # Audit footer
    _audit_footer(c, ctx, pdf_hash, 1)


# ── Page 2 builder ─────────────────────────────────────────────────────────────

def _build_page2(c: Any, ctx: StatementContext, pdf_hash: str) -> None:
    c.showPage()
    c.setPageSize((PAGE_W, PAGE_H))

    c.setFillColor(OFF_WHITE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    _header_plate(c, ctx.agency_name)

    # ── Payment instructions ─────────────────────────────────────────────────
    body_y = PAGE_H - 1.60 * inch
    body_x = 0.55 * inch
    body_w = PAGE_W - 1.10 * inch

    _chamfer_rect(c, body_x, body_y - 2.20 * inch, body_w, 2.20 * inch,
                  cut=6.0, fill_color=CHARCOAL_MID, stroke_color=CHARCOAL_LITE)
    _angled_separator(c, body_x, body_y - 0.10 * inch, body_w)

    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(body_x + 0.15 * inch, body_y - 0.22 * inch, "HOW TO PAY")
    c.setFillColor(OFF_WHITE)
    c.setFont("Helvetica", 8)

    instructions = [
        ("Online (fastest):",
         f"Visit {ctx.pay_url}  —  Secure card payment via Stripe Checkout."),
        ("By Text/SMS:",
         "Reply PAY to the text message sent to your phone. A secure link will be sent."),
        ("By Phone:",
         f"Call {ctx.agency_phone}. We will text a secure payment link to your mobile number."),
        ("", "WE DO NOT ACCEPT CHECKS. DO NOT MAIL PAYMENT."),
    ]
    row_y = body_y - 0.50 * inch
    for label, text in instructions:
        c.setFillColor(ORANGE)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(body_x + 0.15 * inch, row_y, label)
        c.setFillColor(OFF_WHITE)
        c.setFont("Helvetica", 7.5)
        c.drawString(body_x + 1.60 * inch, row_y, text)
        row_y -= 0.35 * inch

    # ── Dispute / Questions section ──────────────────────────────────────────
    disp_y = body_y - 2.60 * inch
    _chamfer_rect(c, body_x, disp_y - 1.20 * inch, body_w, 1.20 * inch,
                  cut=5.0, fill_color=CHARCOAL, stroke_color=CHARCOAL_LITE)
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(body_x + 0.15 * inch, disp_y - 0.22 * inch, "QUESTIONS / BILLING DISPUTES")
    c.setFillColor(OFF_WHITE)
    c.setFont("Helvetica", 7.5)
    dispute_lines = [
        f"Agency:  {ctx.agency_name}   |   Phone: {ctx.agency_phone}",
        "This statement reflects charges for emergency medical transport services rendered as described above.",
        "If you believe there is an error, contact us within 30 days of this statement date.",
        "Insurance adjustments may reduce the amount due. Please allow 30-60 days for insurance processing.",
    ]
    ty = disp_y - 0.48 * inch
    for dl in dispute_lines:
        c.drawString(body_x + 0.15 * inch, ty, dl)
        ty -= 0.18 * inch

    # ── HIPAA notice ─────────────────────────────────────────────────────────
    hipaa_y = disp_y - 2.00 * inch
    _chamfer_rect(c, body_x, hipaa_y - 1.60 * inch, body_w, 1.60 * inch,
                  cut=5.0, fill_color=CHARCOAL_LITE, stroke_color=TICK_GREY)
    c.setFillColor(RED_CRITICAL)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(body_x + 0.15 * inch, hipaa_y - 0.22 * inch, "HIPAA PRIVACY NOTICE")
    c.setFillColor(OFF_WHITE)
    c.setFont("Helvetica", 6.5)
    hipaa_text = (
        "Your health information is protected under HIPAA (Health Insurance Portability and Accountability Act). "
        "This statement is sent to the individual identified above as the patient or responsible party. "
        "We use and disclose your protected health information only as permitted or required by law. "
        "For our full Notice of Privacy Practices, contact the agency at the address above."
    )
    text_y = hipaa_y - 0.48 * inch
    words = hipaa_text.split()
    line_buf: list[str] = []
    for w in words:
        test_line = " ".join(line_buf + [w])
        if c.stringWidth(test_line, "Helvetica", 6.5) > body_w - 0.30 * inch:
            c.drawString(body_x + 0.15 * inch, text_y, " ".join(line_buf))
            text_y -= 9
            line_buf = [w]
        else:
            line_buf.append(w)
    if line_buf:
        c.drawString(body_x + 0.15 * inch, text_y, " ".join(line_buf))

    # Bottom HUD ticks
    _hud_ticks(c, 0.45 * inch, 0.60 * inch, PAGE_W - 0.90 * inch, gap=12.0, length=5.0)

    # Audit footer
    _audit_footer(c, ctx, pdf_hash, 2)


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_billing_statement_pdf(ctx: StatementContext) -> tuple[bytes, str]:
    """
    Returns (pdf_bytes, sha256_hex).
    The hash is computed over the EXACT bytes returned, so callers must hash
    BEFORE sending to Lob; this function does it internally and returns both.
    """
    _require_reportlab()

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))

    # First pass: build with a deterministic per-statement sentinel hash so the
    # first-pass PDF is clearly marked as a pre-image draft.  The real SHA-256
    # of the first-pass bytes is then embedded in the second (final) pass.
    import hashlib as _hl
    SENTINEL = _hl.sha256(f"sentinel:{ctx.statement_id}:{ctx.tenant_id}".encode()).hexdigest()

    _build_page1(c, ctx, SENTINEL)
    _build_page2(c, ctx, SENTINEL)
    c.save()
    first_pass_bytes = buf.getvalue()
    real_hash = hashlib.sha256(first_pass_bytes).hexdigest()

    # Second pass with real hash embedded in footer
    buf2 = io.BytesIO()
    c2 = rl_canvas.Canvas(buf2, pagesize=(PAGE_W, PAGE_H))
    _build_page1(c2, ctx, real_hash)
    _build_page2(c2, ctx, real_hash)
    c2.save()
    final_bytes = buf2.getvalue()

    # The second-pass hash is what we store (bytes containing the real hash string)
    stored_hash = hashlib.sha256(final_bytes).hexdigest()
    return final_bytes, stored_hash
