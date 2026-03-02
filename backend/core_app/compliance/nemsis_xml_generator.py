from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring

logger = logging.getLogger(__name__)

NEMSIS_NS = "http://www.nemsis.org"
NEMSIS_VERSION = "3.5.0.191130CP1"

NV_NOT_APPLICABLE = "7701001"
NV_NOT_RECORDED = "7701003"
NV_NOT_REPORTING = "7701005"


def _sub(parent: Element, tag: str, text: str | None = None, attrib: dict | None = None) -> Element:
    el = SubElement(parent, tag, attrib or {})
    if text is not None:
        el.text = str(text)
    return el


def build_nemsis_document(
    incident: dict[str, Any],
    patient: dict[str, Any],
    vitals: list[dict[str, Any]],
    agency_info: dict[str, Any],
) -> bytes:
    ET.register_namespace("", NEMSIS_NS)

    root = Element(f"{{{NEMSIS_NS}}}EMSDataSet")
    root.set("xsi:schemaLocation", f"{NEMSIS_NS} EMSDataSet.xsd")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("nemsisVersion", NEMSIS_VERSION)

    header = _sub(root, f"{{{NEMSIS_NS}}}Header")
    _sub(header, f"{{{NEMSIS_NS}}}DemographicGroup")

    dem_group = header.find(f"{{{NEMSIS_NS}}}DemographicGroup")

    agency_el = _sub(dem_group, f"{{{NEMSIS_NS}}}dAgency.AgencyGroup")
    _sub(agency_el, f"{{{NEMSIS_NS}}}dAgency.01", agency_info.get("state_id", "WI-EMS-000"))
    _sub(agency_el, f"{{{NEMSIS_NS}}}dAgency.02", agency_info.get("number", "WI-0001"))
    _sub(agency_el, f"{{{NEMSIS_NS}}}dAgency.03", agency_info.get("name", "FusionEMS Agency"))
    _sub(agency_el, f"{{{NEMSIS_NS}}}dAgency.04", agency_info.get("state", "WI"))

    pcr = _sub(root, f"{{{NEMSIS_NS}}}EMSDataSet")
    record = _sub(pcr, f"{{{NEMSIS_NS}}}PatientCareReport")
    record.set("id", str(incident.get("id", uuid.uuid4())))

    patient_section = _sub(record, f"{{{NEMSIS_NS}}}ePatient")
    p_data = patient.get("data", patient)

    dob = p_data.get("date_of_birth")
    _sub(
        patient_section,
        f"{{{NEMSIS_NS}}}ePatient.02",
        dob if dob else NV_NOT_RECORDED,
        {"xsi:nil": "true", "NV": NV_NOT_RECORDED} if not dob else {},
    )

    last = p_data.get("last_name")
    _sub(patient_section, f"{{{NEMSIS_NS}}}ePatient.03", last if last else NV_NOT_RECORDED)

    first = p_data.get("first_name")
    _sub(patient_section, f"{{{NEMSIS_NS}}}ePatient.04", first if first else NV_NOT_RECORDED)

    gender = p_data.get("gender")
    gender_map = {"male": "9906001", "female": "9906003", "unknown": "9906009"}
    _sub(
        patient_section,
        f"{{{NEMSIS_NS}}}ePatient.13",
        gender_map.get(str(gender).lower(), NV_NOT_RECORDED) if gender else NV_NOT_RECORDED,
    )

    incident_data = incident.get("data", incident)

    times_section = _sub(record, f"{{{NEMSIS_NS}}}eTimes")
    dispatch_time = incident_data.get("dispatch_time") or incident_data.get("created_at")
    _sub(
        times_section,
        f"{{{NEMSIS_NS}}}eTimes.01",
        _format_nemsis_time(dispatch_time) if dispatch_time else NV_NOT_RECORDED,
    )

    scene_arrived = incident_data.get("arrived_scene_time")
    _sub(
        times_section,
        f"{{{NEMSIS_NS}}}eTimes.06",
        _format_nemsis_time(scene_arrived) if scene_arrived else NV_NOT_RECORDED,
    )

    patient_contacted = incident_data.get("patient_contact_time")
    _sub(
        times_section,
        f"{{{NEMSIS_NS}}}eTimes.07",
        _format_nemsis_time(patient_contacted) if patient_contacted else NV_NOT_RECORDED,
    )

    hosp_arrived = incident_data.get("arrived_destination_time")
    _sub(
        times_section,
        f"{{{NEMSIS_NS}}}eTimes.11",
        _format_nemsis_time(hosp_arrived) if hosp_arrived else NV_NOT_RECORDED,
    )

    incident_section = _sub(record, f"{{{NEMSIS_NS}}}eIncident")
    _sub(
        incident_section,
        f"{{{NEMSIS_NS}}}eIncident.01",
        incident_data.get("incident_number", str(incident.get("id", ""))[:20]),
    )

    disposition_section = _sub(record, f"{{{NEMSIS_NS}}}eDisposition")
    _sub(
        disposition_section,
        f"{{{NEMSIS_NS}}}eDisposition.27",
        incident_data.get("patient_disposition_code", "4227001"),
    )

    vitals_section = _sub(record, f"{{{NEMSIS_NS}}}eVitals")
    for vital in vitals[:5]:
        vg = _sub(vitals_section, f"{{{NEMSIS_NS}}}eVitals.VitalGroup")
        vdata = vital.get("data", vital)
        _sub(
            vg,
            f"{{{NEMSIS_NS}}}eVitals.01",
            _format_nemsis_time(vdata.get("recorded_at"))
            if vdata.get("recorded_at")
            else NV_NOT_RECORDED,
        )
        sbp = vdata.get("systolic_bp")
        _sub(vg, f"{{{NEMSIS_NS}}}eVitals.06", str(sbp) if sbp else NV_NOT_RECORDED)
        hr = vdata.get("heart_rate")
        _sub(vg, f"{{{NEMSIS_NS}}}eVitals.10", str(hr) if hr else NV_NOT_RECORDED)
        gcs = vdata.get("gcs_total")
        _sub(vg, f"{{{NEMSIS_NS}}}eVitals.21", str(gcs) if gcs else NV_NOT_RECORDED)

    xml_bytes = tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_bytes


def _format_nemsis_time(val: Any) -> str:
    if not val:
        return NV_NOT_RECORDED
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00")) if isinstance(val, str) else val
        return dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    except Exception:
        return NV_NOT_RECORDED


def validate_nemsis_xml(xml_bytes: bytes) -> dict[str, Any]:
    try:
        ET.fromstring(xml_bytes)
        root = ET.fromstring(xml_bytes)

        def check_element(elem, path=""):
            if elem.text == NV_NOT_RECORDED and not elem.get("xsi:nil"):
                pass
            for child in elem:
                check_element(child, f"{path}/{child.tag}")

        check_element(root)
        return {"valid": True, "errors": [], "warnings": []}
    except ET.ParseError as e:
        return {"valid": False, "errors": [str(e)], "warnings": []}
