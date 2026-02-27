from __future__ import annotations
import hashlib, io, json, uuid
from datetime import datetime, timezone
from typing import Any

from core_app.services.domination_service import DominationService
from core_app.core.config import get_settings


class LegalService:
    def __init__(self, db, publisher, tenant_id_override=None):
        self._svc = DominationService(db, publisher)
        settings = get_settings()
        if tenant_id_override:
            self._system_tenant_id = uuid.UUID(str(tenant_id_override))
        elif settings.system_tenant_id:
            self._system_tenant_id = uuid.UUID(settings.system_tenant_id)
        else:
            self._system_tenant_id = uuid.uuid4()

    def create_packet(
        self,
        application_id: str,
        signer_email: str,
        signer_name: str,
        agency_name: str,
        plan_data: dict,
    ) -> dict:
        import asyncio

        packet_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        loop = asyncio.get_event_loop()
        packet = loop.run_until_complete(
            self._svc.create(
                table="legal_packets",
                tenant_id=self._system_tenant_id,
                actor_user_id=None,
                data={
                    "application_id": application_id,
                    "signer_email": signer_email,
                    "signer_name": signer_name,
                    "agency_name": agency_name,
                    "status": "pending",
                    "required_docs": ["BAA", "MSA", "ORDER_FORM"],
                    "plan_data": plan_data,
                    "created_at": now,
                },
                correlation_id=None,
            )
        )

        actual_packet_id = str(packet["id"])
        documents = []
        for doc_type in ("BAA", "MSA", "ORDER_FORM"):
            doc = loop.run_until_complete(
                self._svc.create(
                    table="legal_documents",
                    tenant_id=self._system_tenant_id,
                    actor_user_id=None,
                    data={
                        "packet_id": actual_packet_id,
                        "doc_type": doc_type,
                        "template_version": "1.0",
                        "s3_key_draft": f"legal/{actual_packet_id}/{doc_type}_draft.pdf",
                        "s3_key_executed": None,
                        "sha256": None,
                        "status": "pending",
                    },
                    correlation_id=None,
                )
            )
            documents.append(doc)

        result = dict(packet)
        result["documents"] = documents
        return result

    def get_packet(self, packet_id: str, application_id: str) -> dict | None:
        repo = self._svc.repo("legal_packets")
        records = repo.list(self._system_tenant_id, limit=5000)
        packet = next(
            (
                r
                for r in records
                if str(r["id"]) == packet_id
                and r.get("data", {}).get("application_id") == application_id
            ),
            None,
        )
        if packet is None:
            return None

        doc_repo = self._svc.repo("legal_documents")
        all_docs = doc_repo.list(self._system_tenant_id, limit=5000)
        documents = [d for d in all_docs if d.get("data", {}).get("packet_id") == packet_id]

        result = dict(packet)
        result["documents"] = documents
        return result

    def sign_packet(self, packet_id: str, signing_data: dict) -> dict:
        import asyncio

        consents = signing_data.get("consents", {})
        if not (consents.get("baa") and consents.get("msa") and consents.get("order_form")):
            raise ValueError("All three consents (baa, msa, order_form) must be True to execute signing.")

        repo = self._svc.repo("legal_packets")
        records = repo.list(self._system_tenant_id, limit=5000)
        packet = next((r for r in records if str(r["id"]) == packet_id), None)
        if packet is None:
            raise ValueError(f"Packet {packet_id} not found.")

        packet_data = packet.get("data", {})

        doc_repo = self._svc.repo("legal_documents")
        all_docs = doc_repo.list(self._system_tenant_id, limit=5000)
        packet_docs = [d for d in all_docs if d.get("data", {}).get("packet_id") == packet_id]

        loop = asyncio.get_event_loop()
        settings = get_settings()
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        updated_docs = []
        for doc in packet_docs:
            doc_data = doc.get("data", {})
            doc_type = doc_data.get("doc_type", "")
            pdf_bytes = self._render_executed_pdf(doc_type, packet_data, signing_data)
            sha256 = hashlib.sha256(pdf_bytes).hexdigest()

            s3_key_executed = f"legal/{packet_id}/{doc_type}_executed.pdf"
            if settings.s3_bucket_docs:
                try:
                    from core_app.documents.s3_storage import put_bytes
                    put_bytes(
                        bucket=settings.s3_bucket_docs,
                        key=s3_key_executed,
                        content=pdf_bytes,
                        content_type="application/pdf",
                    )
                except Exception:
                    pass

            updated = loop.run_until_complete(
                self._svc.update(
                    table="legal_documents",
                    tenant_id=self._system_tenant_id,
                    actor_user_id=None,
                    record_id=uuid.UUID(str(doc["id"])),
                    expected_version=doc.get("version", 1),
                    patch={
                        "s3_key_executed": s3_key_executed,
                        "sha256": sha256,
                        "status": "executed",
                    },
                    correlation_id=None,
                )
            )
            updated_docs.append(updated or doc)

            loop.run_until_complete(
                self._svc.create(
                    table="document_events",
                    tenant_id=self._system_tenant_id,
                    actor_user_id=None,
                    data={
                        "document_id": str(doc["id"]),
                        "packet_id": packet_id,
                        "event_type": "signed",
                        "occurred_at": now_iso,
                    },
                    correlation_id=None,
                )
            )

        loop.run_until_complete(
            self._svc.create(
                table="legal_sign_events",
                tenant_id=self._system_tenant_id,
                actor_user_id=None,
                data={
                    "packet_id": packet_id,
                    "signer_name": signing_data.get("signer_name"),
                    "signer_email": signing_data.get("signer_email"),
                    "signer_title": signing_data.get("signer_title"),
                    "ip_address": signing_data.get("ip_address"),
                    "user_agent": signing_data.get("user_agent"),
                    "consents": signing_data.get("consents"),
                    "signature_text": signing_data.get("signature_text"),
                    "signed_at": now_iso,
                },
                correlation_id=None,
            )
        )

        updated_packet = loop.run_until_complete(
            self._svc.update(
                table="legal_packets",
                tenant_id=self._system_tenant_id,
                actor_user_id=None,
                record_id=uuid.UUID(packet_id),
                expected_version=packet.get("version", 1),
                patch={"status": "signed", "signed_at": now_iso},
                correlation_id=None,
            )
        )

        result = dict(updated_packet or packet)
        result["documents"] = updated_docs
        return result

    def _render_executed_pdf(self, doc_type: str, packet_data: dict, signing_data: dict) -> bytes:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch,
            )

            DARK_NAVY = colors.HexColor("#0f1720")
            ACCENT = colors.HexColor("#1a9dff")
            LIGHT_GRAY = colors.HexColor("#c8d0d8")
            WHITE = colors.white
            styles = getSampleStyleSheet()

            header_style = ParagraphStyle(
                "HeaderStyle",
                parent=styles["Normal"],
                fontSize=22,
                textColor=WHITE,
                fontName="Helvetica-Bold",
                alignment=TA_CENTER,
                spaceAfter=4,
            )
            subheader_style = ParagraphStyle(
                "SubHeaderStyle",
                parent=styles["Normal"],
                fontSize=10,
                textColor=LIGHT_GRAY,
                fontName="Helvetica",
                alignment=TA_CENTER,
                spaceAfter=2,
            )
            doc_title_style = ParagraphStyle(
                "DocTitleStyle",
                parent=styles["Normal"],
                fontSize=14,
                textColor=WHITE,
                fontName="Helvetica-Bold",
                alignment=TA_CENTER,
            )
            section_style = ParagraphStyle(
                "SectionStyle",
                parent=styles["Normal"],
                fontSize=11,
                textColor=DARK_NAVY,
                fontName="Helvetica-Bold",
                spaceBefore=14,
                spaceAfter=4,
            )
            body_style = ParagraphStyle(
                "BodyStyle",
                parent=styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#1a2332"),
                fontName="Helvetica",
                leading=14,
                spaceAfter=6,
            )

            agency_name = packet_data.get("agency_name", "Agency")
            signer_name = signing_data.get("signer_name", "")
            signer_email = signing_data.get("signer_email", "")
            signer_title = signing_data.get("signer_title", "")
            signed_at = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
            plan_data = packet_data.get("plan_data", {})

            def header_block(doc_label: str) -> list:
                header_table = Table(
                    [
                        [Paragraph("FusionEMS Quantum", header_style)],
                        [Paragraph("Advanced Emergency Medical Services Platform", subheader_style)],
                        [Paragraph(doc_label, doc_title_style)],
                    ],
                    colWidths=[7.0 * inch],
                )
                header_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), DARK_NAVY),
                            ("TOPPADDING", (0, 0), (-1, -1), 12),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                            ("LEFTPADDING", (0, 0), (-1, -1), 18),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 18),
                        ]
                    )
                )
                return [header_table, Spacer(1, 0.25 * inch)]

            elements: list = []

            if doc_type == "BAA":
                elements += header_block("BUSINESS ASSOCIATE AGREEMENT (BAA)")
                elements.append(Paragraph("Parties", section_style))
                elements.append(Paragraph(
                    f"This Business Associate Agreement (\"BAA\") is entered into as of {signed_at} "
                    f"between <b>FusionEMS Quantum, LLC</b> (\"Business Associate\") and "
                    f"<b>{agency_name}</b> (\"Covered Entity\").",
                    body_style,
                ))
                elements.append(Paragraph("1. Permitted Uses and Disclosures", section_style))
                elements.append(Paragraph(
                    "Business Associate may use or disclose PHI only as necessary to perform the services "
                    "described in the Master Subscription Agreement, or as required by law. Business Associate "
                    "shall not use or disclose PHI in a manner that would violate 45 C.F.R. Parts 164.502 and "
                    "164.504 if done by Covered Entity.",
                    body_style,
                ))
                elements.append(Paragraph("2. Safeguards", section_style))
                elements.append(Paragraph(
                    "Business Associate shall implement administrative, physical, and technical safeguards that "
                    "reasonably and appropriately protect the confidentiality, integrity, and availability of "
                    "electronic PHI (ePHI) as required by the HIPAA Security Rule (45 C.F.R. Part 164, Subpart C). "
                    "Safeguards include AES-256 encryption at rest, TLS 1.2+ in transit, role-based access controls, "
                    "audit logging, and annual workforce training.",
                    body_style,
                ))
                elements.append(Paragraph("3. Breach Notification", section_style))
                elements.append(Paragraph(
                    "Business Associate shall notify Covered Entity without unreasonable delay and in no case "
                    "later than 60 calendar days following discovery of a Breach of Unsecured PHI as defined "
                    "under 45 C.F.R. § 164.402. Notice shall include: (a) identity of each individual whose "
                    "PHI was breached, (b) description of the PHI involved, (c) steps individuals should take "
                    "to protect themselves, (d) description of what Business Associate is doing to investigate, "
                    "mitigate, and prevent future occurrences.",
                    body_style,
                ))
                elements.append(Paragraph("4. Subcontractors", section_style))
                elements.append(Paragraph(
                    "Business Associate shall ensure that any subcontractors or agents that create, receive, "
                    "maintain, or transmit PHI on behalf of Business Associate agree to the same restrictions "
                    "and conditions that apply to Business Associate under this BAA, in accordance with "
                    "45 C.F.R. § 164.308(b)(2).",
                    body_style,
                ))
                elements.append(Paragraph("5. PHI Return and Destruction", section_style))
                elements.append(Paragraph(
                    "Upon termination of the MSA for any reason, Business Associate shall return or destroy "
                    "all PHI received from, or created or received on behalf of, Covered Entity. If return or "
                    "destruction is not feasible, Business Associate shall extend the protections of this BAA "
                    "to that PHI and limit further uses and disclosures to those purposes that make the return "
                    "or destruction infeasible, in compliance with 45 C.F.R. § 164.504(e)(2)(ii)(J).",
                    body_style,
                ))
                elements.append(Paragraph("6. HHS Availability", section_style))
                elements.append(Paragraph(
                    "Business Associate shall make its internal practices, books, and records relating to the "
                    "use and disclosure of PHI received from, or created or received on behalf of, Covered Entity "
                    "available to the Secretary of HHS for purposes of determining Covered Entity's compliance "
                    "with HIPAA, in accordance with 45 C.F.R. § 164.504(e)(2)(ii)(H).",
                    body_style,
                ))
                elements.append(Paragraph("7. Term and Termination", section_style))
                elements.append(Paragraph(
                    "This BAA shall be effective as of the date first set forth above and shall terminate when "
                    "the MSA terminates. Either party may terminate this BAA if the other party has breached a "
                    "material term and has failed to cure within 30 days of written notice.",
                    body_style,
                ))

            elif doc_type == "MSA":
                elements += header_block("MASTER SUBSCRIPTION AGREEMENT (MSA)")
                elements.append(Paragraph("Parties", section_style))
                elements.append(Paragraph(
                    f"This Master Subscription Agreement (\"Agreement\") is entered into as of {signed_at} "
                    f"between <b>FusionEMS Quantum, LLC</b>, a Delaware limited liability company "
                    f"(\"FusionEMS\"), and <b>{agency_name}</b> (\"Customer\").",
                    body_style,
                ))
                elements.append(Paragraph("1. Definitions", section_style))
                elements.append(Paragraph(
                    "<b>\"Platform\"</b> means the FusionEMS Quantum software-as-a-service application and all "
                    "associated APIs, modules, and documentation. <b>\"Subscription\"</b> means Customer's "
                    "right to access and use the Platform under the terms of this Agreement and the applicable "
                    "Order Form. <b>\"Authorized Users\"</b> means Customer's employees, contractors, and agents "
                    "who are permitted to use the Platform.",
                    body_style,
                ))
                elements.append(Paragraph("2. Subscription Scope and Grant of Rights", section_style))
                elements.append(Paragraph(
                    "Subject to the terms of this Agreement and payment of applicable fees, FusionEMS grants "
                    "Customer a non-exclusive, non-transferable, worldwide right to access and use the Platform "
                    "during the Subscription Term solely for Customer's internal business operations. The modules "
                    "and usage tiers are set forth in the Order Form.",
                    body_style,
                ))
                elements.append(Paragraph("3. Support", section_style))
                elements.append(Paragraph(
                    "FusionEMS shall provide standard support via email and in-platform ticketing during "
                    "business hours (9 AM–6 PM ET, Monday–Friday, excluding US federal holidays). Critical "
                    "incident response (Severity 1: Platform down or data inaccessible) shall be addressed "
                    "within 4 hours. Platform availability target is 99.5% monthly uptime, excluding scheduled "
                    "maintenance windows communicated with at least 48 hours advance notice.",
                    body_style,
                ))
                elements.append(Paragraph("4. Fees and Payment", section_style))
                elements.append(Paragraph(
                    "Customer shall pay the fees set forth in the applicable Order Form. Invoices are due "
                    "net-30 from invoice date. Overdue balances accrue interest at 1.5% per month. FusionEMS "
                    "reserves the right to suspend access upon 15 days written notice of non-payment.",
                    body_style,
                ))
                elements.append(Paragraph("5. Customer Responsibilities", section_style))
                elements.append(Paragraph(
                    "Customer is responsible for: (a) maintaining the confidentiality of access credentials; "
                    "(b) ensuring Authorized Users comply with this Agreement; (c) maintaining accurate patient "
                    "and billing data; (d) obtaining all necessary licenses and authorizations to operate EMS "
                    "services in Customer's jurisdiction; (e) notifying FusionEMS immediately of any unauthorized "
                    "access or security incident.",
                    body_style,
                ))
                elements.append(Paragraph("6. No Collections Activity; AI Drafts Disclaimer", section_style))
                elements.append(Paragraph(
                    "FusionEMS is a software technology provider and does not act as a collection agency or "
                    "provide legal, billing, or collection advice. Customer is solely responsible for compliance "
                    "with FDCPA, state collection laws, and payer regulations. AI-generated content (narratives, "
                    "coding suggestions, appeals) is provided as a draft aid only. Customer's licensed clinical "
                    "and billing staff must review, verify, and take responsibility for all submitted claims and "
                    "clinical documentation before submission.",
                    body_style,
                ))
                elements.append(Paragraph("7. Confidentiality", section_style))
                elements.append(Paragraph(
                    "Each party agrees to keep confidential all non-public information of the other party "
                    "designated as confidential or that reasonably should be understood to be confidential "
                    "given the nature of the information and circumstances of disclosure. Neither party shall "
                    "disclose such information to third parties without prior written consent, except to "
                    "employees and contractors on a need-to-know basis under confidentiality obligations.",
                    body_style,
                ))
                elements.append(Paragraph("8. Intellectual Property", section_style))
                elements.append(Paragraph(
                    "FusionEMS retains all right, title, and interest in and to the Platform, including all "
                    "improvements, modifications, and derivative works. Customer retains all right, title, "
                    "and interest in and to Customer Data. Customer grants FusionEMS a limited license to "
                    "process Customer Data solely to provide the Platform services.",
                    body_style,
                ))
                elements.append(Paragraph("9. Warranties and Disclaimer", section_style))
                elements.append(Paragraph(
                    "FusionEMS warrants that the Platform will substantially conform to its documentation "
                    "during the Subscription Term. EXCEPT AS EXPRESSLY SET FORTH HEREIN, THE PLATFORM IS "
                    "PROVIDED \"AS IS\" AND FUSIONEMSQUANTUM DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, "
                    "INCLUDING WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.",
                    body_style,
                ))
                elements.append(Paragraph("10. Limitation of Liability", section_style))
                elements.append(Paragraph(
                    "IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, "
                    "EXEMPLARY, OR CONSEQUENTIAL DAMAGES. FUSIONEMSQUANTUM'S AGGREGATE LIABILITY SHALL NOT "
                    "EXCEED THE FEES PAID BY CUSTOMER IN THE 12 MONTHS PRECEDING THE CLAIM.",
                    body_style,
                ))
                elements.append(Paragraph("11. Term and Termination", section_style))
                elements.append(Paragraph(
                    "The initial Subscription Term is set forth in the Order Form. Either party may terminate "
                    "for material breach upon 30 days written notice if the breach is not cured within that "
                    "period. Upon termination, Customer's access to the Platform will cease and FusionEMS will "
                    "make Customer Data available for export for 60 days before deletion.",
                    body_style,
                ))
                elements.append(Paragraph("12. Data Export", section_style))
                elements.append(Paragraph(
                    "Upon request at any time during the Subscription Term, or within 60 days following "
                    "termination, FusionEMS shall provide Customer with a complete export of Customer Data "
                    "in standard formats (CSV, HL7 FHIR JSON, or NEMSIS XML as applicable).",
                    body_style,
                ))
                elements.append(Paragraph("13. Governing Law", section_style))
                elements.append(Paragraph(
                    "This Agreement shall be governed by and construed in accordance with the laws of the "
                    "State of Delaware, without regard to conflict of law principles. Any disputes shall be "
                    "resolved by binding arbitration under AAA rules in Wilmington, Delaware.",
                    body_style,
                ))

            elif doc_type == "ORDER_FORM":
                elements += header_block("ORDER FORM")
                elements.append(Paragraph("Order Details", section_style))
                elements.append(Paragraph(
                    f"This Order Form is incorporated into and governed by the Master Subscription Agreement "
                    f"between <b>FusionEMS Quantum, LLC</b> and <b>{agency_name}</b>, effective {signed_at}.",
                    body_style,
                ))

                modules = plan_data.get("selected_modules", plan_data.get("modules", []))
                call_volume = plan_data.get("annual_call_volume", plan_data.get("call_volume_tier", "N/A"))
                monthly_base = plan_data.get("monthly_base", plan_data.get("base_price", "Per Quote"))
                agency_type = plan_data.get("agency_type", "EMS")
                per_claim_trigger = plan_data.get(
                    "per_claim_trigger",
                    "Per-claim fee applies when claim is submitted to payer, per the active pricing schedule.",
                )

                order_table_data = [
                    ["Field", "Value"],
                    ["Agency Name", agency_name],
                    ["Agency Type", agency_type],
                    ["Annual Call Volume Tier", str(call_volume)],
                    ["Monthly Base Fee", str(monthly_base)],
                    ["Selected Modules", ", ".join(modules) if modules else "Standard Suite"],
                    ["Per-Claim Trigger", per_claim_trigger],
                    ["Subscription Term", "12 months, auto-renewing"],
                    ["Billing Cycle", "Monthly"],
                    ["Payment Method", "ACH / Credit Card on file"],
                ]
                order_table = Table(order_table_data, colWidths=[2.5 * inch, 4.5 * inch])
                order_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), DARK_NAVY),
                            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4f8"), WHITE]),
                            ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
                            ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                        ]
                    )
                )
                elements.append(order_table)
                elements.append(Spacer(1, 0.15 * inch))
                elements.append(Paragraph("Module Descriptions", section_style))
                module_descriptions = {
                    "billing": "Automated EMS billing, claim generation, payer submission, and denial management.",
                    "transportlink": "Electronic transport manifests, hospital notifications, and divert status integration.",
                    "crewlink": "Crew scheduling, certification tracking, shift management, and compliance monitoring.",
                    "patient_portal": "Secure patient-facing portal for statement viewing, payment, and records requests.",
                    "ai_narrative": "AI-assisted clinical narrative generation with provider review workflow.",
                    "nemsis_export": "NEMSIS 3.5.1-compliant PCR export for state reporting requirements.",
                    "auto_appeals": "Automated insurance denial appeals with AI-generated appeal letters.",
                    "fire_module": "Fire incident reporting, resource tracking, and NFIRS-compatible export.",
                    "cad_module": "CAD integration bridge for real-time dispatch data ingestion.",
                }
                for mod in (modules if modules else []):
                    desc = module_descriptions.get(mod, "Platform module — see documentation for details.")
                    elements.append(Paragraph(f"<b>{mod}:</b> {desc}", body_style))

            elements.append(Spacer(1, 0.3 * inch))
            elements.append(HRFlowable(width="100%", thickness=1.5, color=DARK_NAVY))
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph("Audit Signature Page", section_style))
            consents = signing_data.get("consents", {})
            audit_data = [
                ["Signer Name", signer_name],
                ["Signer Email", signer_email],
                ["Signer Title", signer_title],
                ["Signature Text", signing_data.get("signature_text", "")],
                ["Signed At", signed_at],
                ["IP Address", signing_data.get("ip_address", "")],
                ["User Agent", signing_data.get("user_agent", "")],
                ["BAA Consent", "ACCEPTED" if consents.get("baa") else "NOT ACCEPTED"],
                ["MSA Consent", "ACCEPTED" if consents.get("msa") else "NOT ACCEPTED"],
                ["Order Form Consent", "ACCEPTED" if consents.get("order_form") else "NOT ACCEPTED"],
            ]
            audit_table = Table(audit_data, colWidths=[2.0 * inch, 5.0 * inch])
            audit_table.setStyle(
                TableStyle(
                    [
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f7f9fc"), WHITE]),
                        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ]
                )
            )
            elements.append(audit_table)

            doc.build(elements)
            buffer.seek(0)
            return buffer.read()

        except ImportError:
            lines = [
                b"%PDF-1.4\n",
                b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
                b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            ]
            text_content = (
                f"FusionEMS Quantum\n"
                f"Document Type: {doc_type}\n"
                f"Agency: {packet_data.get('agency_name', '')}\n"
                f"Signer: {signing_data.get('signer_name', '')} <{signing_data.get('signer_email', '')}>\n"
                f"Title: {signing_data.get('signer_title', '')}\n"
                f"Signed At: {datetime.now(timezone.utc).isoformat()}\n"
                f"IP: {signing_data.get('ip_address', '')}\n"
                f"Signature: {signing_data.get('signature_text', '')}\n"
                f"BAA Consent: {signing_data.get('consents', {}).get('baa')}\n"
                f"MSA Consent: {signing_data.get('consents', {}).get('msa')}\n"
                f"Order Form Consent: {signing_data.get('consents', {}).get('order_form')}\n"
            ).encode("utf-8")
            text_len = len(text_content)
            page_stream = (
                f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Contents 4 0 R /Resources << /Font << /F1 << /Type /Font "
                f"/Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
                f"4 0 obj\n<< /Length {text_len} >>\nstream\n"
            ).encode("utf-8")
            trailer = (
                f"\nendstream\nendobj\n"
                f"xref\n0 5\n0000000000 65535 f\n"
                f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n9\n%%EOF\n"
            ).encode("utf-8")
            return b"".join(lines) + page_stream + text_content + trailer

    def get_legal_status(self, application_id: str) -> dict:
        repo = self._svc.repo("legal_packets")
        records = repo.list(self._system_tenant_id, limit=5000)
        packet = next(
            (r for r in records if r.get("data", {}).get("application_id") == application_id),
            None,
        )
        if packet is None:
            return {"signed": False, "packet_id": None, "documents": [], "signed_at": None}

        packet_id = str(packet["id"])
        packet_data = packet.get("data", {})

        doc_repo = self._svc.repo("legal_documents")
        all_docs = doc_repo.list(self._system_tenant_id, limit=5000)
        documents = [d for d in all_docs if d.get("data", {}).get("packet_id") == packet_id]

        signed = packet_data.get("status") == "signed"
        return {
            "signed": signed,
            "packet_id": packet_id,
            "documents": documents,
            "signed_at": packet_data.get("signed_at"),
        }
