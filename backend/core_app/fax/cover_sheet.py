from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from typing import Any

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image,
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
    b"(PDF generation requires reportlab)Tj ET\nendstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n0000000000 65535 f \n"
    b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF"
)

BRAND_DARK = colors.HexColor("#0f1720") if RL_AVAILABLE else None
BRAND_BLUE = colors.HexColor("#3182ce") if RL_AVAILABLE else None
BRAND_LIGHT = colors.HexColor("#e2e8f0") if RL_AVAILABLE else None
BRAND_WHITE = colors.white if RL_AVAILABLE else None
BRAND_GOLD = colors.HexColor("#f6c90e") if RL_AVAILABLE else None


def _styles():
    base = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "FQHeader",
        parent=base["Normal"],
        fontSize=10,
        textColor=BRAND_WHITE,
        fontName="Helvetica",
        spaceAfter=2,
    )
    title_style = ParagraphStyle(
        "FQTitle",
        parent=base["Heading1"],
        fontSize=20,
        textColor=BRAND_DARK,
        fontName="Helvetica-Bold",
        spaceAfter=8,
        spaceBefore=12,
    )
    section_style = ParagraphStyle(
        "FQSection",
        parent=base["Heading2"],
        fontSize=12,
        textColor=BRAND_DARK,
        fontName="Helvetica-Bold",
        spaceAfter=6,
        spaceBefore=10,
    )
    body_style = ParagraphStyle(
        "FQBody",
        parent=base["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#1a202c"),
        spaceAfter=4,
    )
    bold_style = ParagraphStyle(
        "FQBold",
        parent=base["Normal"],
        fontSize=11,
        textColor=BRAND_DARK,
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )
    instruction_style = ParagraphStyle(
        "FQInstruction",
        parent=base["Normal"],
        fontSize=16,
        textColor=BRAND_DARK,
        fontName="Helvetica-Bold",
        spaceAfter=4,
        alignment=1,
    )
    footer_style = ParagraphStyle(
        "FQFooter",
        parent=base["Normal"],
        fontSize=8,
        textColor=colors.grey,
        alignment=1,
    )
    return {
        "header": header_style,
        "title": title_style,
        "section": section_style,
        "body": body_style,
        "bold": bold_style,
        "instruction": instruction_style,
        "footer": footer_style,
    }


def _build_header_table(agency_name: str, s: dict) -> Table:
    data = [[
        Paragraph("<b>FusionEMS Quantum</b>", s["header"]),
        Paragraph(f"<b>{agency_name}</b>", ParagraphStyle(
            "RightHeader",
            parent=s["header"],
            alignment=2,
        )),
    ]]
    t = Table(data, colWidths=[3.5 * inch, 3.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, -1), BRAND_WHITE),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _qr_image(payload_str: str) -> Any | None:
    if not QR_AVAILABLE:
        return None
    try:
        qr = qrcode.QRCode(
            version=4,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=2,
        )
        qr.add_data(payload_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Image(buf, width=2 * inch, height=2 * inch)
    except Exception:
        return None


def _barcode_image(code_value: str) -> Any | None:
    if not BARCODE_AVAILABLE:
        return None
    try:
        buf = io.BytesIO()
        bc = barcode.get("code128", code_value[:20], writer=ImageWriter())
        bc.write(buf, options={"write_text": False, "module_width": 1.5, "module_height": 8.0})
        buf.seek(0)
        return Image(buf, width=2.5 * inch, height=0.9 * inch)
    except Exception:
        return None


def _checkbox_row(doc_types: list[str], active_type: str, s: dict) -> Table:
    row = []
    for dt in doc_types:
        filled = "[\u2612]" if dt.lower() == active_type.lower() else "[\u2610]"
        row.append(Paragraph(f"{filled} {dt}", s["body"]))
    t = Table([row], colWidths=[inch * 7.0 / len(doc_types)] * len(doc_types))
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
    ]))
    return t


class CoverSheetGenerator:
    def generate_claim_cover_sheet(
        self,
        claim_id: str,
        tenant_id: str,
        doc_type: str,
        agency_name: str,
        fax_number: str,
        patient_initials: str = "",
        encounter_date: str = "",
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
        s = _styles()
        story: list[Any] = []

        story.append(_build_header_table(agency_name, s))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("DOCUMENT ROUTING COVER SHEET", s["title"]))
        story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE))
        story.append(Spacer(1, 0.15 * inch))

        claim_display = f"{claim_id[:8]}..." if len(claim_id) > 8 else claim_id
        ref_data = [
            ["Claim Reference", claim_display, "Patient Initials", patient_initials or "—"],
            ["Encounter Date", encounter_date or "—", "Tenant", tenant_id[:8] + "..."],
        ]
        ref_table = Table(ref_data, colWidths=[1.5 * inch, 2 * inch, 1.5 * inch, 2 * inch])
        ref_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f4f8")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f0f4f8")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(ref_table)
        story.append(Spacer(1, 0.2 * inch))

        qr_payload = json.dumps({
            "claim_id": claim_id,
            "tenant_id": tenant_id,
            "doc_type": doc_type,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        qr_img = _qr_image(qr_payload)
        bc_img = _barcode_image(claim_id[:20])

        if qr_img or bc_img:
            img_cells = [qr_img or Paragraph("QR unavailable", s["body"]),
                         bc_img or Paragraph("Barcode unavailable", s["body"])]
            col_widths = [2.2 * inch, 3 * inch]
            img_table = Table([img_cells], colWidths=col_widths)
            img_table.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
            ]))
            story.append(img_table)
            story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Document Type", s["section"]))
        doc_types = ["PCS", "Insurance Card", "Face Sheet", "Authorization", "Denial Letter", "Other"]
        story.append(_checkbox_row(doc_types, doc_type, s))
        story.append(Spacer(1, 0.25 * inch))

        instruction_bg_data = [[
            Paragraph(f"FAX TO: {fax_number}", s["instruction"]),
        ]]
        instruction_table = Table(instruction_bg_data, colWidths=[7 * inch])
        instruction_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff8e1")),
            ("BOX", (0, 0), (-1, -1), 2, BRAND_GOLD),
            ("PADDING", (0, 0), (-1, -1), 14),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(instruction_table)
        story.append(Spacer(1, 0.1 * inch))

        story.append(Paragraph(
            "Include this cover sheet as PAGE 1. Fax separately per patient.",
            ParagraphStyle("inst_sub", parent=s["body"], alignment=1, fontSize=10),
        ))
        story.append(Spacer(1, 0.3 * inch))

        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_LIGHT))
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph("FusionEMS Quantum — Automated Document Routing", s["footer"]))

        doc.build(story)
        return buf.getvalue()

    def generate_agency_doc_kit(
        self,
        agency_name: str,
        tenant_id: str,
        fax_number: str,
        inbound_email: str,
        upload_url: str,
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
        s = _styles()
        story: list[Any] = []

        story.append(_build_header_table(agency_name, s))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("DOCUMENT ROUTING COVER SHEET (TEMPLATE)", s["title"]))
        story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE))
        story.append(Spacer(1, 0.15 * inch))

        blank_data = [
            ["Claim Reference", "", "Patient Initials", ""],
            ["Encounter Date", "", "Tenant ID", tenant_id[:8] + "..."],
        ]
        blank_table = Table(blank_data, colWidths=[1.5 * inch, 2 * inch, 1.5 * inch, 2 * inch])
        blank_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f4f8")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f0f4f8")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(blank_table)
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Document Type", s["section"]))
        doc_types = ["PCS", "Insurance Card", "Face Sheet", "Authorization", "Denial Letter", "Other"]
        story.append(_checkbox_row(doc_types, "", s))
        story.append(Spacer(1, 0.25 * inch))

        instr_data = [[Paragraph(f"FAX TO: {fax_number}", s["instruction"])]]
        instr_table = Table(instr_data, colWidths=[7 * inch])
        instr_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff8e1")),
            ("BOX", (0, 0), (-1, -1), 2, BRAND_GOLD),
            ("PADDING", (0, 0), (-1, -1), 14),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(instr_table)
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(
            "Include this cover sheet as PAGE 1. Fax separately per patient.",
            ParagraphStyle("inst_sub_b", parent=s["body"], alignment=1, fontSize=10),
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_LIGHT))
        story.append(Paragraph("FusionEMS Quantum — Automated Document Routing", s["footer"]))

        story.append(PageBreak())

        story.append(_build_header_table(agency_name, s))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("How to Send Documents", s["title"]))
        story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE))
        story.append(Spacer(1, 0.15 * inch))

        fax_block = [[Paragraph(f"FAX: {fax_number}", ParagraphStyle(
            "BigFax", parent=s["body"], fontSize=22, fontName="Helvetica-Bold",
            textColor=BRAND_DARK, alignment=1,
        ))]]
        fax_table = Table(fax_block, colWidths=[7 * inch])
        fax_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4f8")),
            ("BOX", (0, 0), (-1, -1), 1, BRAND_BLUE),
            ("PADDING", (0, 0), (-1, -1), 14),
        ]))
        story.append(fax_table)
        story.append(Spacer(1, 0.15 * inch))

        contact_data = [
            ["Email", inbound_email],
            ["Portal Upload", upload_url],
        ]
        contact_table = Table(contact_data, colWidths=[1.5 * inch, 5.5 * inch])
        contact_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f4f8")),
        ]))
        story.append(contact_table)
        story.append(Spacer(1, 0.15 * inch))

        upload_qr = _qr_image(upload_url)
        if upload_qr:
            story.append(Paragraph("Scan to upload directly:", s["bold"]))
            story.append(upload_qr)
            story.append(Spacer(1, 0.1 * inch))

        story.append(Paragraph("Step-by-Step Instructions", s["section"]))
        steps = [
            "1. Print this cover sheet.",
            "2. Fill in the Claim Reference, Patient Initials, and Encounter Date.",
            "3. Check the box for the Document Type you are sending.",
            "4. Place this cover sheet as PAGE 1 of your fax.",
            "5. Fax to the number above OR email to the address listed.",
            "6. Alternatively, upload directly to the portal using the QR code or URL above.",
            "7. Send one fax per patient. Do not combine multiple patients in one fax.",
        ]
        for step in steps:
            story.append(Paragraph(step, s["body"]))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_LIGHT))
        story.append(Paragraph("FusionEMS Quantum — Automated Document Routing", s["footer"]))

        story.append(PageBreak())

        story.append(_build_header_table(agency_name, s))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("Request Templates", s["title"]))
        story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE))
        story.append(Spacer(1, 0.15 * inch))

        templates = [
            (
                "PCS Request",
                f"To Whom It May Concern,\n\nWe are requesting a Physician Certification Statement (PCS) for the following patient:\n\n"
                f"Patient Name: ______________________________\n"
                f"Date of Birth: ____/____/______\n"
                f"Date of Service: ____/____/______\n"
                f"Transport Type: [ ] BLS  [ ] ALS  [ ] CCT\n\n"
                f"Please fax completed form to: {fax_number}\n\n"
                f"Thank you,\n{agency_name}",
            ),
            (
                "Insurance Verification Request",
                f"To Whom It May Concern,\n\nWe are requesting insurance verification for the following patient:\n\n"
                f"Patient Name: ______________________________\n"
                f"Member ID: ______________________________\n"
                f"Group Number: ______________________________\n"
                f"Date of Service: ____/____/______\n\n"
                f"Please confirm coverage and benefits by return fax to: {fax_number}\n\n"
                f"Thank you,\n{agency_name}",
            ),
            (
                "Signature Request",
                f"To Whom It May Concern,\n\nWe require an authorized patient or representative signature for billing purposes.\n\n"
                f"Patient Name: ______________________________\n"
                f"Date of Service: ____/____/______\n\n"
                f"Please sign below and return by fax to: {fax_number}\n\n"
                f"Signature: ______________________________  Date: ____/____/______\n\n"
                f"Thank you,\n{agency_name}",
            ),
        ]
        for tmpl_title, tmpl_body in templates:
            story.append(Paragraph(tmpl_title, s["section"]))
            letter_data = [[Paragraph(tmpl_body.replace("\n", "<br/>"), s["body"])]]
            letter_table = Table(letter_data, colWidths=[7 * inch])
            letter_table.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("PADDING", (0, 0), (-1, -1), 10),
            ]))
            story.append(letter_table)
            story.append(Spacer(1, 0.15 * inch))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_LIGHT))
        story.append(Paragraph("FusionEMS Quantum — Automated Document Routing", s["footer"]))

        story.append(PageBreak())

        story.append(_build_header_table(agency_name, s))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("Quick Reference — Documents by Scenario", s["title"]))
        story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE))
        story.append(Spacer(1, 0.15 * inch))

        qr_table_data = [
            ["Scenario", "Required Documents", "Where to Upload"],
            [
                "IFT (Interfacility Transfer)",
                "PCS, Face Sheet, Insurance Card, Signature",
                "Portal → Cases → Upload Docs",
            ],
            [
                "CCT (Critical Care Transport)",
                "PCS, Medical Records, Insurance Card, Authorization, Signature",
                "Portal → Cases → Upload Docs",
            ],
            [
                "911 Emergency",
                "Insurance Card (if available), Face Sheet, Signature",
                "Portal → Cases → Upload Docs",
            ],
            [
                "Denial Appeal",
                "Denial Letter, Medical Records, PCS, Supporting Clinical Notes",
                "Portal → Claims → Appeal",
            ],
        ]
        qr_ref_table = Table(qr_table_data, colWidths=[1.8 * inch, 3.2 * inch, 2 * inch])
        qr_ref_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(qr_ref_table)
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Portal Access", s["section"]))
        portal_data = [
            ["Function", "Portal Location"],
            ["Upload Documents", "Cases → [Case ID] → Documents → Upload"],
            ["View Claim Status", "Claims → [Claim ID] → Status History"],
            ["Submit Appeal", "Claims → [Claim ID] → Appeal → Draft"],
            ["Download Cover Sheet", "Cases → [Case ID] → Doc Kit → Generate"],
            ["View Missing Docs", "Cases → [Case ID] → Checklist"],
        ]
        portal_table = Table(portal_data, colWidths=[2.5 * inch, 4.5 * inch])
        portal_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(portal_table)
        story.append(Spacer(1, 0.2 * inch))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_LIGHT))
        story.append(Paragraph("FusionEMS Quantum — Automated Document Routing", s["footer"]))

        doc.build(story)
        return buf.getvalue()
