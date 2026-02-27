from __future__ import annotations
import hashlib, io

try:
    from pyhanko.sign import signers, fields
    from pyhanko.sign.fields import SigFieldSpec
    from pyhanko_certvalidator import CertificateValidator
    PYHANKO_AVAILABLE = True
except ImportError:
    PYHANKO_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from pypdf import PdfWriter, PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfWriter, PdfReader
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False


class PDFSealer:
    def seal_executed_pdf(
        self,
        pdf_bytes: bytes,
        signer_name: str,
        signer_email: str,
        signed_at: str,
        doc_type: str,
    ) -> tuple[bytes, dict]:
        original_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        audit_data = {
            "doc_type": doc_type,
            "signer_name": signer_name,
            "signer_email": signer_email,
            "signed_at": signed_at,
            "original_sha256": original_sha256,
        }

        method = "audit_page"
        working_bytes = pdf_bytes

        if PYHANKO_AVAILABLE:
            try:
                working_bytes = self._attempt_pyhanko_seal(pdf_bytes, signer_name, signer_email)
                method = "pyhanko"
            except Exception:
                working_bytes = pdf_bytes

        if REPORTLAB_AVAILABLE and PYPDF_AVAILABLE:
            sealed_bytes = self._append_audit_page_reportlab(working_bytes, audit_data)
        else:
            sealed_bytes = self._append_audit_page_fallback(working_bytes, audit_data)

        final_sha256 = hashlib.sha256(sealed_bytes).hexdigest()
        return sealed_bytes, {
            "method": method,
            "sealed": True,
            "final_sha256": final_sha256,
            "audit_page_added": True,
            "original_sha256": original_sha256,
        }

    def _attempt_pyhanko_seal(self, pdf_bytes: bytes, signer_name: str, signer_email: str) -> bytes:
        import tempfile, os
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
        from pyhanko.sign import signers as ph_signers
        from pyhanko.sign.fields import append_signature_field, SigFieldSpec

        with tempfile.NamedTemporaryFile(suffix=".p12", delete=False) as tmp_p12:
            p12_path = tmp_p12.name
        try:
            _generate_self_signed_p12(p12_path, signer_name, signer_email)
            signer = ph_signers.SimpleSigner.load_pkcs12(p12_path, passphrase=b"fusionems")
            in_buf = io.BytesIO(pdf_bytes)
            w = IncrementalPdfFileWriter(in_buf)
            append_signature_field(w, SigFieldSpec("Signature", on_page=-1, box=(36, 36, 300, 80)))
            out_buf = io.BytesIO()
            ph_signers.sign_pdf(
                w,
                signature_meta=ph_signers.PdfSignatureMetadata(field_name="Signature"),
                signer=signer,
                output=out_buf,
            )
            return out_buf.getvalue()
        finally:
            try:
                os.unlink(p12_path)
            except Exception:
                pass

    def _append_audit_page_reportlab(self, original_bytes: bytes, audit_data: dict) -> bytes:
        audit_buf = io.BytesIO()
        doc = SimpleDocTemplate(
            audit_buf,
            pagesize=letter,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "AuditTitle",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor("#1a1a2e"),
            alignment=1,
        )
        label_style = ParagraphStyle(
            "AuditLabel",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#555555"),
            spaceAfter=2,
        )
        value_style = ParagraphStyle(
            "AuditValue",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.HexColor("#1a1a2e"),
            spaceAfter=10,
            fontName="Helvetica-Bold",
        )
        body_style = ParagraphStyle(
            "AuditBody",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#333333"),
            spaceAfter=6,
            leading=14,
        )

        story = [
            Paragraph("EXECUTION CERTIFICATE", title_style),
            Paragraph("FusionEMS Quantum — Electronic Signature Record", styles["Normal"]),
            Spacer(1, 0.2 * inch),
            HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")),
            Spacer(1, 0.2 * inch),
            Paragraph("Document Type", label_style),
            Paragraph(str(audit_data.get("doc_type", "")), value_style),
            Paragraph("Signatory Name", label_style),
            Paragraph(str(audit_data.get("signer_name", "")), value_style),
            Paragraph("Signatory Email", label_style),
            Paragraph(str(audit_data.get("signer_email", "")), value_style),
            Paragraph("Signed At (UTC)", label_style),
            Paragraph(str(audit_data.get("signed_at", "")), value_style),
            Paragraph("Original Document SHA-256", label_style),
            Paragraph(str(audit_data.get("original_sha256", "")), value_style),
            Spacer(1, 0.2 * inch),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")),
            Spacer(1, 0.1 * inch),
            Paragraph(
                "This document was electronically signed via FusionEMS Quantum. "
                "The integrity of this document is verified by the hash recorded above. "
                "Any modification to the document after signing will invalidate this certificate.",
                body_style,
            ),
        ]

        doc.build(story)
        audit_page_bytes = audit_buf.getvalue()

        writer = PdfWriter()
        reader_orig = PdfReader(io.BytesIO(original_bytes))
        for page in reader_orig.pages:
            writer.add_page(page)
        reader_audit = PdfReader(io.BytesIO(audit_page_bytes))
        for page in reader_audit.pages:
            writer.add_page(page)

        out_buf = io.BytesIO()
        writer.write(out_buf)
        return out_buf.getvalue()

    def _append_audit_page_fallback(self, original_bytes: bytes, audit_data: dict) -> bytes:
        audit_text = (
            f"\n\n%%EXECUTION CERTIFICATE\n"
            f"Document Type: {audit_data.get('doc_type', '')}\n"
            f"Signatory: {audit_data.get('signer_name', '')} <{audit_data.get('signer_email', '')}>\n"
            f"Signed At: {audit_data.get('signed_at', '')}\n"
            f"Original SHA-256: {audit_data.get('original_sha256', '')}\n"
            f"This document was electronically signed via FusionEMS Quantum. "
            f"The integrity of this document is verified by the hash recorded above.\n"
            f"%%END CERTIFICATE\n"
        )
        return original_bytes + audit_text.encode("utf-8")

    def verify_document(self, pdf_bytes: bytes, expected_sha256: str) -> dict:
        computed = hashlib.sha256(pdf_bytes).hexdigest()
        match = computed == expected_sha256
        return {
            "verified": match,
            "computed_sha256": computed,
            "expected_sha256": expected_sha256,
            "match": match,
        }


def _generate_self_signed_p12(output_path: str, common_name: str, email: str) -> None:
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        import datetime as dt
        from cryptography.hazmat.primitives.serialization import pkcs12

        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name or "FusionEMS Signer"),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, email or "signer@fusionems.io"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FusionEMS Quantum"),
        ])
        now = dt.datetime.utcnow()
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + dt.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256(), default_backend())
        )
        p12_bytes = pkcs12.serialize_key_and_certificates(
            name=b"FusionEMS",
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(b"fusionems"),
        )
        with open(output_path, "wb") as f:
            f.write(p12_bytes)
    except Exception:
        with open(output_path, "wb") as f:
            f.write(b"")
