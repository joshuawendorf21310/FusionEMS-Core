from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from typing import Any

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


BRAND_DARK = colors.HexColor("#0f1720") if REPORTLAB_AVAILABLE else None
BRAND_BLUE = colors.HexColor("#3182ce") if REPORTLAB_AVAILABLE else None
BRAND_LIGHT = colors.HexColor("#e2e8f0") if REPORTLAB_AVAILABLE else None


def _require_reportlab():
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab not installed. Run: pip install reportlab")


def generate_roi_proposal_pdf(roi_data: dict[str, Any], agency_info: dict[str, Any]) -> bytes:
    _require_reportlab()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"], fontSize=24, textColor=BRAND_DARK, spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "subtitle", parent=styles["Normal"], fontSize=12, textColor=BRAND_BLUE, spaceAfter=20
    )
    section_style = ParagraphStyle(
        "section",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=BRAND_DARK,
        spaceBefore=16,
        spaceAfter=8,
    )
    body_style = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, spaceAfter=6)

    story = []

    story.append(Paragraph("FusionEMS Quantum", title_style))
    story.append(Paragraph("Revenue Intelligence Platform — Agency Proposal", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE))
    story.append(Spacer(1, 0.2 * inch))

    agency_name = agency_info.get("name", "Your Agency")
    story.append(Paragraph(f"Prepared for: <b>{agency_name}</b>", body_style))
    story.append(Paragraph(f"Date: {datetime.now(UTC).strftime('%B %d, %Y')}", body_style))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Revenue Opportunity Analysis", section_style))

    calls = roi_data.get("annual_calls", 0)
    gross = roi_data.get("gross_revenue_cents", 0)
    uplift = roi_data.get("revenue_uplift_cents", 0)
    denial_reduction = roi_data.get("denial_reduction_cents", 0)

    roi_table_data = [
        ["Metric", "Current Est.", "With FusionEMS", "Improvement"],
        ["Annual Transports", f"{calls:,}", f"{calls:,}", "—"],
        [
            "Gross Revenue",
            f"${gross / 100:,.0f}",
            f"${(gross + uplift) / 100:,.0f}",
            f"+${uplift / 100:,.0f}",
        ],
        [
            "Denial Rate",
            f"{roi_data.get('current_denial_rate', 12):.0f}%",
            f"{roi_data.get('projected_denial_rate', 6):.0f}%",
            f"-{roi_data.get('current_denial_rate', 12) - roi_data.get('projected_denial_rate', 6):.0f}%",
        ],
        [
            "Recovery from Denials",
            "—",
            f"${denial_reduction / 100:,.0f}",
            f"+${denial_reduction / 100:,.0f}",
        ],
    ]

    t = Table(roi_table_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRAND_LIGHT, colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Why FusionEMS Quantum", section_style))
    features = [
        (
            "Overlay Mode",
            "Keep your existing ePCR. Plug in billing intelligence without rip-and-replace.",
        ),
        (
            "Transparent Pricing",
            "Base fee + per-transport. No percentage cuts. See exactly what you pay.",
        ),
        ("Certification Ready", "Built for NEMSIS 3.5.1 + Wisconsin profile from day one."),
        ("Real-Time Operations", "Live dashboard, AI denial alerts, WebSocket event feed."),
        (
            "Self-Service Onboarding",
            "ROI → Proposal → Sign → Pay → Deploy. No sales calls required.",
        ),
    ]
    for feat_title, feat_desc in features:
        story.append(Paragraph(f"<b>{feat_title}:</b> {feat_desc}", body_style))

    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_LIGHT))
    story.append(
        Paragraph(
            "FusionEMS Quantum is designed for certification readiness. "
            "Not certified. Platform is in active development targeting Wisconsin NEMSIS certification.",
            ParagraphStyle(
                "disclaimer", parent=styles["Normal"], fontSize=8, textColor=colors.grey
            ),
        )
    )

    doc.build(story)
    return buf.getvalue()


def generate_contract_pdf(
    agency_info: dict[str, Any],
    pricing_info: dict[str, Any],
    contract_id: str | None = None,
) -> bytes:
    _require_reportlab()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter, leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(
        Paragraph(
            "FusionEMS Quantum",
            ParagraphStyle("h1", parent=styles["Heading1"], fontSize=20, textColor=BRAND_DARK),
        )
    )
    story.append(
        Paragraph(
            "Master Subscription Agreement",
            ParagraphStyle("h2", parent=styles["Heading2"], fontSize=14),
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE))
    story.append(Spacer(1, 0.2 * inch))

    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, spaceAfter=8, leading=14)
    story.append(Paragraph(f"Contract ID: {contract_id or str(uuid.uuid4())[:8].upper()}", body))
    story.append(Paragraph(f"Date: {datetime.now(UTC).strftime('%B %d, %Y')}", body))
    story.append(Paragraph(f"Agency: {agency_info.get('name', 'Agency Name')}", body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(
        Paragraph(
            "Subscription Terms",
            ParagraphStyle("h3", parent=styles["Heading3"], fontSize=12, textColor=BRAND_DARK),
        )
    )
    base_fee = pricing_info.get("base_monthly_cents", 0)
    per_call = pricing_info.get("per_call_cents", 0)
    story.append(Paragraph(f"Base Monthly Fee: ${base_fee / 100:,.2f}/month", body))
    story.append(Paragraph(f"Per-Transport Fee: ${per_call / 100:.2f}/transport", body))
    story.append(Paragraph("Billing: Monthly in arrears via Stripe.", body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(
        Paragraph(
            "Terms",
            ParagraphStyle("h3", parent=styles["Heading3"], fontSize=12, textColor=BRAND_DARK),
        )
    )
    terms_text = [
        "1. This agreement governs access to FusionEMS Quantum platform services.",
        "2. Subscriber agrees to comply with all applicable HIPAA requirements.",
        "3. Platform is provided 'as is' and is designed for certification readiness, not certified.",
        "4. Either party may terminate with 30 days written notice.",
        "5. Data ownership remains with the Subscriber at all times.",
        "6. FusionEMS will execute a BAA upon request.",
    ]
    for term in terms_text:
        story.append(Paragraph(term, body))

    story.append(Spacer(1, 0.5 * inch))
    sig_data = [
        ["Agency Authorized Signatory", "FusionEMS Quantum"],
        ["", ""],
        ["Signature: ______________________", "Signature: ______________________"],
        ["Name: ______________________", "Name: ______________________"],
        ["Title: ______________________", "Title: ______________________"],
        ["Date: ______________________", "Date: ______________________"],
    ]
    sig_table = Table(sig_data, colWidths=[3.5 * inch, 3.5 * inch])
    sig_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(sig_table)

    doc.build(story)
    return buf.getvalue()


def generate_baa_pdf(agency_info: dict[str, Any]) -> bytes:
    _require_reportlab()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter, leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch
    )
    styles = getSampleStyleSheet()
    story = []
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, spaceAfter=8, leading=14)

    story.append(
        Paragraph(
            "BUSINESS ASSOCIATE AGREEMENT",
            ParagraphStyle(
                "h1", parent=styles["Heading1"], fontSize=18, textColor=BRAND_DARK, alignment=1
            ),
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE))
    story.append(Spacer(1, 0.2 * inch))

    story.append(
        Paragraph(
            f"This Business Associate Agreement ('BAA') is entered into between {agency_info.get('name', 'Covered Entity')} ('Covered Entity') and FusionEMS Quantum ('Business Associate').",
            body,
        )
    )
    story.append(Spacer(1, 0.1 * inch))

    baa_sections = [
        (
            "1. Definitions",
            "Terms used herein shall have the meanings set forth in 45 CFR §160.103 and §164.304.",
        ),
        (
            "2. Permitted Uses",
            "Business Associate may use and disclose PHI only as necessary to provide the services described in the underlying agreement.",
        ),
        (
            "3. Safeguards",
            "Business Associate shall implement appropriate administrative, physical, and technical safeguards to protect the confidentiality, integrity, and availability of PHI.",
        ),
        (
            "4. Breach Notification",
            "Business Associate shall notify Covered Entity without unreasonable delay, and no later than 60 days, following discovery of a breach of unsecured PHI.",
        ),
        (
            "5. Term and Termination",
            "This BAA is effective upon signing and remains in effect until the underlying service agreement is terminated.",
        ),
        (
            "6. Return/Destruction of PHI",
            "Upon termination, Business Associate shall return or destroy all PHI, if feasible.",
        ),
    ]
    for title, text in baa_sections:
        story.append(
            Paragraph(
                title,
                ParagraphStyle("h3", parent=styles["Heading3"], fontSize=11, textColor=BRAND_DARK),
            )
        )
        story.append(Paragraph(text, body))

    story.append(Spacer(1, 0.5 * inch))
    story.append(
        Paragraph(
            "IN WITNESS WHEREOF, the parties have executed this BAA as of the date signed below.",
            body,
        )
    )
    story.append(Spacer(1, 0.3 * inch))

    sig_data = [
        ["Covered Entity", "Business Associate (FusionEMS Quantum)"],
        ["Signature: ______________________", "Signature: ______________________"],
        ["Date: ______________________", "Date: ______________________"],
    ]
    t = Table(sig_data, colWidths=[3.5 * inch, 3.5 * inch])
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 10), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.append(t)

    doc.build(story)
    return buf.getvalue()
