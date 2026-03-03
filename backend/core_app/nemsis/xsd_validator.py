from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

XSD_BASE = Path(__file__).resolve().parent.parent.parent / "compliance" / "nemsis" / "v3.5.1"


@dataclass
class XSDValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    xsd_version: str = "3.5.1"

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "xsd_version": self.xsd_version,
        }


class NEMSISXSDValidator:
    def __init__(self, xsd_dir: Optional[str] = None):
        self._xsd_dir = Path(xsd_dir) if xsd_dir else XSD_BASE
        self._ems_schema = None
        self._dem_schema = None

    def _load_schema(self, schema_path: Path):
        try:
            from lxml import etree

            with open(schema_path, "rb") as f:
                schema_doc = etree.parse(f)
            return etree.XMLSchema(schema_doc)
        except ImportError:
            return None
        except Exception:
            return None

    def _find_xsd(self, pattern: str) -> Optional[Path]:
        for p in self._xsd_dir.rglob(pattern):
            return p
        return None

    def validate_ems_dataset(self, xml_content: str | bytes) -> XSDValidationResult:
        return self._validate(xml_content, "EMS")

    def validate_dem_dataset(self, xml_content: str | bytes) -> XSDValidationResult:
        return self._validate(xml_content, "DEM")

    def _validate(self, xml_content: str | bytes, dataset_type: str) -> XSDValidationResult:
        result = XSDValidationResult(valid=True)

        if isinstance(xml_content, str):
            xml_content = xml_content.encode("utf-8")

        try:
            from lxml import etree
        except ImportError:
            result.warnings.append("lxml not installed; falling back to xml.etree structural check")
            return self._structural_validate(xml_content, dataset_type, result)

        try:
            doc = etree.fromstring(xml_content)
        except etree.XMLSyntaxError as e:
            result.valid = False
            result.errors.append(f"XML parse error: {e}")
            return result

        xsd_file = self._find_xsd(f"*{dataset_type}*DataSet*.xsd")
        if not xsd_file:
            xsd_file = self._find_xsd("*.xsd")

        if xsd_file:
            schema = self._load_schema(xsd_file)
            if schema:
                if not schema.validate(doc):
                    result.valid = False
                    for error in schema.error_log:
                        result.errors.append(f"Line {error.line}: {error.message}")
            else:
                result.warnings.append(f"Could not load XSD schema from {xsd_file}")
        else:
            result.warnings.append(f"No XSD file found for {dataset_type} dataset in {self._xsd_dir}")

        root_tag = etree.QName(doc.tag).localname if doc.tag else ""
        if dataset_type == "EMS" and "EMS" not in root_tag.upper():
            result.warnings.append(f"Root element '{root_tag}' may not be an EMS dataset")
        elif dataset_type == "DEM" and "DEM" not in root_tag.upper():
            result.warnings.append(f"Root element '{root_tag}' may not be a DEM dataset")

        return result

    def _structural_validate(
        self, xml_content: bytes, dataset_type: str, result: XSDValidationResult
    ) -> XSDValidationResult:
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            result.valid = False
            result.errors.append(f"XML parse error: {e}")
            return result

        if dataset_type == "EMS":
            required_sections = ["eRecord", "ePatient", "eResponse", "eTimes"]
            ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
            for section in required_sections:
                found = root.find(f".//{ns}{section}")
                if found is None:
                    found = root.find(f".//*[local-name()='{section}']")
                if found is None:
                    result.warnings.append(f"Expected EMS section '{section}' not found")

        return result
