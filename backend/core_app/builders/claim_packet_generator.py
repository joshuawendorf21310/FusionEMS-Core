from __future__ import annotations

import base64
import io
from datetime import datetime, timezone
from typing import Any

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        HRFlowable,
        PageBreak,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False

_FALLBACK_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 52>>stream\nBT /F1 12 Tf 72 720 Td"
    b"(PDF generation requires reportlab or weasyprint)Tj ET\nendstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n0000000000 65535 f \n"
    b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF"
)

BRAND_DARK = colors.HexColor("#0f1720") if RL_AVAILABLE else None
BRAND_BLUE = colors.HexColor("#3182ce") if RL_AVAILABLE else None
BRAND_LIGHT = colors.HexColor("#e2e8f0") if RL_AVAILABLE else None
BRAND_WHITE = colors.white if RL_AVAILABLE else None
BRAND_STRIPE_A = colors.HexColor("#f8fafc") if RL_AVAILABLE else None


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")


def _rl_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("CPH1", parent=base["Heading1"], fontSize=20, textColor=BRAND_DARK, fontName="Helvetica-Bold", spaceAfter=6),
        "h2": ParagraphStyle("CPH2", parent=base["Heading2"], fontSize=13, textColor=BRAND_DARK, fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=6),
        "h3": ParagraphStyle("CPH3", parent=base["Heading3"], fontSize=11, textColor=BRAND_DARK, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("CPBody", parent=base["Normal"], fontSize=9, spaceAfter=3, leading=13),
        "label": ParagraphStyle("CPLabel", parent=base["Normal"], fontSize=9, fontName="Helvetica-Bold", spaceAfter=2),
        "small": ParagraphStyle("CPSmall", parent=base["Normal"], fontSize=8, textColor=colors.grey, spaceAfter=2),
        "footer": ParagraphStyle("CPFooter", parent=base["Normal"], fontSize=8, textColor=colors.grey, alignment=1),
        "mono": ParagraphStyle("CPMono", parent=base["Code"], fontSize=8, fontName="Courier", spaceAfter=2),
    }


def _rl_header(story: list, title: str, s: dict, agency_name: str = "") -> None:
    header_data = [[
        Paragraph("<b>FusionEMS Quantum</b>", ParagraphStyle("HdrL", parent=s["body"], textColor=BRAND_WHITE, fontName="Helvetica-Bold", fontSize=11)),
        Paragraph(f"<b>{title}</b>", ParagraphStyle("HdrC", parent=s["body"], textColor=BRAND_WHITE, fontName="Helvetica-Bold", fontSize=11, alignment=1)),
        Paragraph(f"{agency_name}<br/><font size=8>CONFIDENTIAL</font>", ParagraphStyle("HdrR", parent=s["body"], textColor=BRAND_WHITE, fontSize=9, alignment=2)),
    ]]
    ht = Table(header_data, colWidths=[2.5 * inch, 3 * inch, 1.5 * inch])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(ht)
    story.append(Spacer(1, 0.15 * inch))


def _rl_kv_table(pairs: list[tuple[str, str]], s: dict, col_widths: list | None = None) -> Table:
    data = [[Paragraph(k, s["label"]), Paragraph(str(v) if v else "—", s["body"])] for k, v in pairs]
    widths = col_widths or [1.8 * inch, 5.2 * inch]
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f4f8")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e0")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    return t


def _rl_data_table(headers: list[str], rows: list[list[str]], s: dict, col_widths: list | None = None) -> Table:
    header_row = [Paragraph(h, ParagraphStyle("TH", parent=s["label"], textColor=BRAND_WHITE, fontSize=9)) for h in headers]
    data_rows = []
    for row in rows:
        data_rows.append([Paragraph(str(c) if c else "—", s["body"]) for c in row])

    all_data = [header_row] + data_rows
    total_width = 7.0 * inch
    widths = col_widths or [total_width / len(headers)] * len(headers)

    t = Table(all_data, colWidths=widths)
    stripe_colors = [BRAND_STRIPE_A, BRAND_WHITE]
    row_bg_cmds = []
    for i, _ in enumerate(data_rows):
        row_bg_cmds.append(("BACKGROUND", (0, i + 1), (-1, i + 1), stripe_colors[i % 2]))

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e0")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ] + row_bg_cmds
    t.setStyle(TableStyle(style_cmds))
    return t


def _rl_footer(story: list, s: dict) -> None:
    story.append(Spacer(1, 0.15 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_LIGHT))
    story.append(Paragraph("FusionEMS Quantum | Confidential", s["footer"]))


class ClaimPacketGenerator:
    def generate_claim_packet(
        self,
        claim_data: dict,
        patient_data: dict,
        attachments: list[dict],
        include_audit: bool = True,
    ) -> bytes:
        if not WEASYPRINT_AVAILABLE and not RL_AVAILABLE:
            return _FALLBACK_PDF

        if WEASYPRINT_AVAILABLE:
            html = self._build_weasyprint_html(claim_data, patient_data, attachments, include_audit)
            try:
                return HTML(string=html).write_pdf()
            except Exception:
                pass

        if RL_AVAILABLE:
            return self._build_reportlab_packet(claim_data, patient_data, attachments, include_audit)

        return _FALLBACK_PDF

    def _build_weasyprint_html(
        self,
        claim_data: dict,
        patient_data: dict,
        attachments: list[dict],
        include_audit: bool,
    ) -> str:
        claim_id = claim_data.get("claim_id") or claim_data.get("id") or "N/A"
        patient_name = f"{patient_data.get('first_name', '')} {patient_data.get('last_name', '')}".strip() or "N/A"
        dob = patient_data.get("dob") or "N/A"
        dos = claim_data.get("dos") or claim_data.get("encounter_date") or "N/A"
        payer = claim_data.get("payer_name") or "N/A"
        member_id = claim_data.get("member_id") or "N/A"
        total_charges = claim_data.get("total_charges") or claim_data.get("billed_amount_cents", 0)
        if isinstance(total_charges, (int, float)) and total_charges > 100:
            total_charges_display = f"${total_charges / 100:,.2f}"
        else:
            total_charges_display = f"${float(total_charges):,.2f}" if total_charges else "N/A"

        service_lines = claim_data.get("service_lines") or []
        sl_rows = ""
        for sl in service_lines:
            code = sl.get("procedure_code", "")
            mods = ", ".join(sl.get("modifiers") or [])
            sl_date = sl.get("dos") or dos
            charge = sl.get("charge", 0)
            units = sl.get("units", 1)
            charge_display = f"${float(charge):,.2f}" if charge else "N/A"
            sl_rows += f"<tr><td>{code}</td><td>{mods}</td><td>{sl_date}</td><td>{units}</td><td>{charge_display}</td></tr>"

        attachments_rows = ""
        for att in attachments:
            attachments_rows += (
                f"<tr>"
                f"<td>{att.get('doc_type', 'N/A')}</td>"
                f"<td>{att.get('filename') or att.get('s3_key', 'N/A')}</td>"
                f"<td>{att.get('received_date') or att.get('created_at', 'N/A')}</td>"
                f"<td>{(att.get('sha256') or '')[:8] or 'N/A'}</td>"
                f"</tr>"
            )

        audit_section = ""
        if include_audit:
            audit_history = claim_data.get("audit_trail") or []
            audit_rows = ""
            for ev in audit_history:
                audit_rows += (
                    f"<tr>"
                    f"<td>{ev.get('action', 'N/A')}</td>"
                    f"<td>{ev.get('actor', 'N/A')}</td>"
                    f"<td>{ev.get('occurred_at', 'N/A')}</td>"
                    f"<td>{ev.get('detail', '')}</td>"
                    f"</tr>"
                )
            audit_section = f"""
            <section>
              <h2>Section 6: Audit Trail</h2>
              <table>
                <thead><tr><th>Action</th><th>Actor</th><th>Timestamp</th><th>Detail</th></tr></thead>
                <tbody>{audit_rows or "<tr><td colspan='4'>No audit events recorded.</td></tr>"}</tbody>
              </table>
            </section>
            """

        epcr_narrative = (claim_data.get("epcr_narrative") or "")[:500]
        assessment_notes = (claim_data.get("assessment_notes") or "")[:300]

        generated_at = _now_str()
        claim_id_short = str(claim_id)[:8]

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>FusionEMS Quantum — Claim Packet</title>
<style>
  @page {{ margin: 1in 0.75in; @bottom-center {{ content: "FusionEMS Quantum | Confidential | Page " counter(page) " of " counter(pages); font-size: 8pt; color: #718096; }} }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 9pt; color: #1a202c; background: #fff; }}
  .page-header {{ background: #0f1720; color: #fff; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }}
  .page-header .brand {{ font-size: 13pt; font-weight: bold; }}
  .page-header .meta {{ font-size: 8pt; text-align: right; }}
  .confidential {{ font-size: 8pt; color: #a0aec0; letter-spacing: 1px; text-transform: uppercase; }}
  h2 {{ font-size: 12pt; color: #0f1720; border-bottom: 2px solid #3182ce; padding-bottom: 4px; margin: 18px 0 10px; }}
  h3 {{ font-size: 10pt; color: #0f1720; margin: 12px 0 6px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 8.5pt; }}
  thead tr {{ background: #0f1720; color: #fff; }}
  thead th {{ padding: 7px 8px; text-align: left; font-weight: bold; }}
  tbody tr:nth-child(even) {{ background: #f8fafc; }}
  tbody tr:nth-child(odd) {{ background: #fff; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
  .kv-table td:first-child {{ background: #f0f4f8; font-weight: bold; width: 180px; }}
  .narrative {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 10px; font-size: 8.5pt; line-height: 1.5; margin-bottom: 10px; white-space: pre-wrap; }}
  section {{ margin-bottom: 24px; }}
  .page-break {{ page-break-after: always; }}
</style>
</head>
<body>
<div class="page-header">
  <div class="brand">FusionEMS Quantum</div>
  <div style="text-align:center;font-size:11pt;font-weight:bold;">CLAIM PACKET</div>
  <div class="meta">Claim: {claim_id_short}...<br/>Generated: {generated_at}<br/><span class="confidential">Confidential</span></div>
</div>

<section>
  <h2>Section 1: Claim Summary</h2>
  <table class="kv-table">
    <tbody>
      <tr><td>Claim ID</td><td>{claim_id}</td></tr>
      <tr><td>Patient Name</td><td>{patient_name}</td></tr>
      <tr><td>Date of Birth</td><td>{dob}</td></tr>
      <tr><td>Date of Service</td><td>{dos}</td></tr>
      <tr><td>Payer</td><td>{payer}</td></tr>
      <tr><td>Member ID</td><td>{member_id}</td></tr>
      <tr><td>Total Charges</td><td>{total_charges_display}</td></tr>
      <tr><td>Transport Type</td><td>{claim_data.get('transport_type') or claim_data.get('service_level') or 'N/A'}</td></tr>
      <tr><td>Origin</td><td>{claim_data.get('origin_address') or 'N/A'}</td></tr>
      <tr><td>Destination</td><td>{claim_data.get('destination_address') or 'N/A'}</td></tr>
    </tbody>
  </table>
</section>

<section>
  <h2>Section 2: Service Lines</h2>
  <table>
    <thead><tr><th>CPT/HCPCS</th><th>Modifiers</th><th>Date</th><th>Units</th><th>Charge</th></tr></thead>
    <tbody>{sl_rows or "<tr><td colspan='5'>No service lines recorded.</td></tr>"}</tbody>
  </table>
</section>

<section>
  <h2>Section 3: Patient Signatures</h2>
  <table>
    <thead><tr><th>Signature Type</th><th>Status</th><th>Collected Date</th><th>Reference</th></tr></thead>
    <tbody>
      {"".join(
          f"<tr><td>{s.get('sig_type','N/A')}</td><td>{s.get('status','N/A')}</td><td>{s.get('collected_at','N/A')}</td><td>{s.get('reference_id','N/A')}</td></tr>"
          for s in (claim_data.get("signatures") or [])
      ) or "<tr><td colspan='4'>No signature records on file.</td></tr>"}
    </tbody>
  </table>
</section>

<section>
  <h2>Section 4: Clinical Documentation Summary</h2>
  <h3>ePCR Narrative</h3>
  <div class="narrative">{epcr_narrative or "No narrative available."}</div>
  <h3>Assessment Notes</h3>
  <div class="narrative">{assessment_notes or "No assessment notes available."}</div>
</section>

<section>
  <h2>Section 5: Attached Documents</h2>
  <table>
    <thead><tr><th>Document Type</th><th>File / S3 Key</th><th>Received Date</th><th>SHA256 (8 chars)</th></tr></thead>
    <tbody>{attachments_rows or "<tr><td colspan='4'>No documents attached.</td></tr>"}</tbody>
  </table>
</section>

{audit_section}

</body>
</html>"""
        return html

    def _build_reportlab_packet(
        self,
        claim_data: dict,
        patient_data: dict,
        attachments: list[dict],
        include_audit: bool,
    ) -> bytes:
        if not RL_AVAILABLE:
            return _FALLBACK_PDF

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.6 * inch,
        )
        s = _rl_styles()
        story: list[Any] = []

        claim_id = str(claim_data.get("claim_id") or claim_data.get("id") or "N/A")
        patient_name = f"{patient_data.get('first_name', '')} {patient_data.get('last_name', '')}".strip() or "N/A"
        agency_name = claim_data.get("agency_name") or ""

        _rl_header(story, "CLAIM PACKET", s, agency_name)

        story.append(Paragraph("Section 1: Claim Summary", s["h2"]))
        summary_pairs = [
            ("Claim ID", claim_id),
            ("Patient Name", patient_name),
            ("Date of Birth", patient_data.get("dob") or "N/A"),
            ("Date of Service", claim_data.get("dos") or claim_data.get("encounter_date") or "N/A"),
            ("Payer", claim_data.get("payer_name") or "N/A"),
            ("Member ID", claim_data.get("member_id") or "N/A"),
            ("Total Charges", str(claim_data.get("total_charges") or claim_data.get("billed_amount_cents") or "N/A")),
            ("Transport Type", claim_data.get("transport_type") or claim_data.get("service_level") or "N/A"),
            ("Origin", claim_data.get("origin_address") or "N/A"),
            ("Destination", claim_data.get("destination_address") or "N/A"),
        ]
        story.append(_rl_kv_table(summary_pairs, s))

        story.append(Paragraph("Section 2: Service Lines", s["h2"]))
        sl_headers = ["CPT/HCPCS", "Modifiers", "Date", "Units", "Charge"]
        sl_rows_data: list[list[str]] = []
        for sl in (claim_data.get("service_lines") or []):
            sl_rows_data.append([
                sl.get("procedure_code", ""),
                ", ".join(sl.get("modifiers") or []),
                sl.get("dos") or claim_data.get("dos") or "",
                str(sl.get("units", 1)),
                f"${float(sl.get('charge', 0)):,.2f}",
            ])
        if not sl_rows_data:
            sl_rows_data = [["No service lines", "", "", "", ""]]
        story.append(_rl_data_table(sl_headers, sl_rows_data, s, col_widths=[1.2 * inch, 1.5 * inch, 1.2 * inch, 0.7 * inch, 1.4 * inch]))

        story.append(Paragraph("Section 3: Patient Signatures", s["h2"]))
        sig_headers = ["Signature Type", "Status", "Collected Date", "Reference"]
        sig_rows: list[list[str]] = []
        for sig in (claim_data.get("signatures") or []):
            sig_rows.append([
                sig.get("sig_type", "N/A"),
                sig.get("status", "N/A"),
                sig.get("collected_at", "N/A"),
                sig.get("reference_id", "N/A"),
            ])
        if not sig_rows:
            sig_rows = [["No signature records on file.", "", "", ""]]
        story.append(_rl_data_table(sig_headers, sig_rows, s))

        story.append(Paragraph("Section 4: Clinical Documentation Summary", s["h2"]))
        story.append(Paragraph("ePCR Narrative", s["h3"]))
        narrative = (claim_data.get("epcr_narrative") or "No narrative available.")[:500]
        story.append(Paragraph(narrative, s["body"]))
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("Assessment Notes", s["h3"]))
        notes = (claim_data.get("assessment_notes") or "No assessment notes available.")[:300]
        story.append(Paragraph(notes, s["body"]))

        story.append(Paragraph("Section 5: Attached Documents", s["h2"]))
        att_headers = ["Document Type", "File / S3 Key", "Received Date", "SHA256 (8 chars)"]
        att_rows: list[list[str]] = []
        for att in attachments:
            att_rows.append([
                att.get("doc_type", "N/A"),
                att.get("filename") or att.get("s3_key", "N/A"),
                att.get("received_date") or att.get("created_at", "N/A"),
                (att.get("sha256") or "")[:8] or "N/A",
            ])
        if not att_rows:
            att_rows = [["No documents attached.", "", "", ""]]
        story.append(_rl_data_table(att_headers, att_rows, s))

        if include_audit:
            story.append(Paragraph("Section 6: Audit Trail", s["h2"]))
            audit_headers = ["Action", "Actor", "Timestamp", "Detail"]
            audit_rows: list[list[str]] = []
            for ev in (claim_data.get("audit_trail") or []):
                audit_rows.append([
                    ev.get("action", "N/A"),
                    ev.get("actor", "N/A"),
                    ev.get("occurred_at", "N/A"),
                    ev.get("detail", ""),
                ])
            if not audit_rows:
                audit_rows = [["No audit events recorded.", "", "", ""]]
            story.append(_rl_data_table(audit_headers, audit_rows, s))

        _rl_footer(story, s)
        doc.build(story)
        return buf.getvalue()

    def generate_epcr_summary_page(self, chart_data: dict) -> bytes:
        if not WEASYPRINT_AVAILABLE and not RL_AVAILABLE:
            return _FALLBACK_PDF

        if WEASYPRINT_AVAILABLE:
            incident_time = chart_data.get("incident_time") or "N/A"
            dispatch_time = chart_data.get("dispatch_time") or "N/A"
            on_scene_time = chart_data.get("on_scene_time") or "N/A"
            transport_time = chart_data.get("transport_time") or "N/A"
            vitals = chart_data.get("vitals") or []
            medications = chart_data.get("medications") or []
            procedures = chart_data.get("procedures") or []
            disposition = chart_data.get("disposition") or "N/A"
            chief_complaint = chart_data.get("chief_complaint") or "N/A"
            age = chart_data.get("patient_age") or "N/A"
            gender = chart_data.get("patient_gender") or "N/A"

            vitals_rows = ""
            for v in vitals[:5]:
                vitals_rows += (
                    f"<tr>"
                    f"<td>{v.get('time','')}</td>"
                    f"<td>{v.get('bp','')}</td>"
                    f"<td>{v.get('hr','')}</td>"
                    f"<td>{v.get('rr','')}</td>"
                    f"<td>{v.get('spo2','')}</td>"
                    f"<td>{v.get('gcs','')}</td>"
                    f"</tr>"
                )

            meds_rows = ""
            for m in medications[:10]:
                meds_rows += f"<tr><td>{m.get('name','')}</td><td>{m.get('dose','')}</td><td>{m.get('route','')}</td><td>{m.get('time','')}</td></tr>"

            proc_rows = ""
            for p in procedures[:10]:
                proc_rows += f"<tr><td>{p.get('name','')}</td><td>{p.get('time','')}</td><td>{p.get('provider','')}</td></tr>"

            generated_at = _now_str()
            html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/>
<title>ePCR Summary</title>
<style>
  @page {{ margin: 0.75in; @bottom-center {{ content: "FusionEMS Quantum | Confidential | ePCR Summary"; font-size: 8pt; color: #718096; }} }}
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #1a202c; }}
  .header {{ background: #0f1720; color: #fff; padding: 10px 14px; display: flex; justify-content: space-between; margin-bottom: 14px; }}
  h2 {{ font-size: 11pt; color: #0f1720; border-bottom: 1.5px solid #3182ce; padding-bottom: 3px; margin: 14px 0 8px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 8.5pt; }}
  thead tr {{ background: #0f1720; color: #fff; }}
  th, td {{ padding: 5px 7px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
  tr:nth-child(even) {{ background: #f8fafc; }}
  .kv td:first-child {{ background: #f0f4f8; font-weight: bold; width: 160px; }}
</style>
</head><body>
<div class="header">
  <strong>FusionEMS Quantum</strong>
  <span style="font-size:11pt;font-weight:bold;">ePCR SUMMARY PAGE</span>
  <span style="font-size:8pt;text-align:right;">Generated: {generated_at}<br/>CONFIDENTIAL</span>
</div>
<h2>Patient &amp; Incident</h2>
<table class="kv"><tbody>
  <tr><td>Age</td><td>{age}</td></tr>
  <tr><td>Gender</td><td>{gender}</td></tr>
  <tr><td>Chief Complaint</td><td>{chief_complaint}</td></tr>
  <tr><td>Incident Time</td><td>{incident_time}</td></tr>
  <tr><td>Dispatch Time</td><td>{dispatch_time}</td></tr>
  <tr><td>On Scene</td><td>{on_scene_time}</td></tr>
  <tr><td>Transport Time</td><td>{transport_time}</td></tr>
  <tr><td>Disposition</td><td>{disposition}</td></tr>
</tbody></table>
<h2>Vitals Summary</h2>
<table>
  <thead><tr><th>Time</th><th>BP</th><th>HR</th><th>RR</th><th>SpO2</th><th>GCS</th></tr></thead>
  <tbody>{vitals_rows or "<tr><td colspan='6'>No vitals recorded.</td></tr>"}</tbody>
</table>
<h2>Medications</h2>
<table>
  <thead><tr><th>Medication</th><th>Dose</th><th>Route</th><th>Time</th></tr></thead>
  <tbody>{meds_rows or "<tr><td colspan='4'>No medications administered.</td></tr>"}</tbody>
</table>
<h2>Procedures</h2>
<table>
  <thead><tr><th>Procedure</th><th>Time</th><th>Provider</th></tr></thead>
  <tbody>{proc_rows or "<tr><td colspan='3'>No procedures performed.</td></tr>"}</tbody>
</table>
</body></html>"""
            try:
                return HTML(string=html).write_pdf()
            except Exception:
                pass

        if RL_AVAILABLE:
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                                    topMargin=0.6 * inch, bottomMargin=0.6 * inch)
            s = _rl_styles()
            story: list[Any] = []
            _rl_header(story, "ePCR SUMMARY PAGE", s)

            kv_pairs = [
                ("Age", str(chart_data.get("patient_age") or "N/A")),
                ("Gender", str(chart_data.get("patient_gender") or "N/A")),
                ("Chief Complaint", str(chart_data.get("chief_complaint") or "N/A")),
                ("Incident Time", str(chart_data.get("incident_time") or "N/A")),
                ("Dispatch Time", str(chart_data.get("dispatch_time") or "N/A")),
                ("On Scene", str(chart_data.get("on_scene_time") or "N/A")),
                ("Transport Time", str(chart_data.get("transport_time") or "N/A")),
                ("Disposition", str(chart_data.get("disposition") or "N/A")),
            ]
            story.append(_rl_kv_table(kv_pairs, s))

            story.append(Paragraph("Vitals Summary", s["h2"]))
            v_headers = ["Time", "BP", "HR", "RR", "SpO2", "GCS"]
            v_rows = [[str(v.get(k.lower(), "")) for k in ["time", "bp", "hr", "rr", "spo2", "gcs"]] for v in (chart_data.get("vitals") or [])]
            if not v_rows:
                v_rows = [["No vitals", "", "", "", "", ""]]
            story.append(_rl_data_table(v_headers, v_rows, s))

            story.append(Paragraph("Medications", s["h2"]))
            m_headers = ["Medication", "Dose", "Route", "Time"]
            m_rows = [[str(m.get(k, "")) for k in ["name", "dose", "route", "time"]] for m in (chart_data.get("medications") or [])]
            if not m_rows:
                m_rows = [["No medications", "", "", ""]]
            story.append(_rl_data_table(m_headers, m_rows, s))

            story.append(Paragraph("Procedures", s["h2"]))
            p_headers = ["Procedure", "Time", "Provider"]
            p_rows = [[str(p.get(k, "")) for k in ["name", "time", "provider"]] for p in (chart_data.get("procedures") or [])]
            if not p_rows:
                p_rows = [["No procedures", "", ""]]
            story.append(_rl_data_table(p_headers, p_rows, s))

            _rl_footer(story, s)
            doc.build(story)
            return buf.getvalue()

        return _FALLBACK_PDF
