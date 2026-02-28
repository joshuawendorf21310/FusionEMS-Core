from __future__ import annotations

from datetime import datetime
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.etree.ElementTree as ET

NEMSIS_NS = "http://www.nemsis.org"
NEMSIS_VERSION = "3.5.0.191130CP1"
NV_NOT_RECORDED = "7701003"
NV_NOT_APPLICABLE = "7701001"
NV_NOT_REPORTING = "7701005"

GENDER_MAP = {
    "male": "9906001", "female": "9906003", "unknown": "9906009",
    "other": "9906011", "transgender_male": "9906007", "transgender_female": "9906005",
}
RACE_MAP = {
    "white": "2514001", "black": "2514003", "asian": "2514005",
    "native": "2514007", "pacific": "2514009", "other": "2514011", "hispanic": "2514013",
}
TRANSPORT_MODE_MAP = {
    "emergent": "4233001", "non_emergent": "4233003", "cancel": "4233005",
}
LEVEL_OF_CARE_MAP = {
    "bls": "9917001", "als": "9917003", "cct": "9917007", "hems": "9917011",
}


class NEMSISExporter:
    def _sub(self, parent: Element, tag: str, text: str | None = None, attrib: dict | None = None) -> Element:
        el = SubElement(parent, tag, attrib or {})
        if text is not None:
            el.text = str(text)
        return el

    def _fmt_time(self, val: Any) -> str:
        if not val:
            return NV_NOT_RECORDED
        try:
            if isinstance(val, str):
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            elif isinstance(val, datetime):
                dt = val
            else:
                return NV_NOT_RECORDED
            return dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        except Exception:
            return NV_NOT_RECORDED

    def _nv(self, val: Any) -> str:
        if val is None:
            return NV_NOT_RECORDED
        s = str(val).strip()
        return s if s else NV_NOT_RECORDED

    def _ns(self, tag: str) -> str:
        return f"{{{NEMSIS_NS}}}{tag}"

    def export_chart(self, chart_dict: dict[str, Any], agency_info: dict[str, Any]) -> bytes:
        ET.register_namespace("", NEMSIS_NS)

        root = Element(self._ns("EMSDataSet"))
        root.set("xsi:schemaLocation", f"{NEMSIS_NS} EMSDataSet.xsd")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set("nemsisVersion", NEMSIS_VERSION)

        header = self._sub(root, self._ns("Header"))
        dem_group = self._sub(header, self._ns("DemographicGroup"))
        agency_el = self._sub(dem_group, self._ns("dAgency.AgencyGroup"))
        self._sub(agency_el, self._ns("dAgency.01"), agency_info.get("state_id", "WI-EMS-000"))
        self._sub(agency_el, self._ns("dAgency.02"), agency_info.get("number", "WI-0001"))
        self._sub(agency_el, self._ns("dAgency.03"), agency_info.get("name", "FusionEMS Agency"))
        self._sub(agency_el, self._ns("dAgency.04"), agency_info.get("state", "WI"))

        pcr_wrapper = self._sub(root, self._ns("EMSDataSet"))
        record = self._sub(pcr_wrapper, self._ns("PatientCareReport"))
        record.set("id", chart_dict["chart_id"])

        dispatch = chart_dict.get("dispatch", {})
        patient = chart_dict.get("patient", {})
        disposition = chart_dict.get("disposition", {})
        assessments = chart_dict.get("assessments", [])
        primary = next((a for a in assessments if a.get("assessment_type") == "primary"), assessments[0] if assessments else {})

        erecord = self._sub(record, self._ns("eRecord"))
        self._sub(erecord, self._ns("eRecord.01"), chart_dict["chart_id"])

        eresponse = self._sub(record, self._ns("eResponse"))
        self._sub(eresponse, self._ns("eResponse.13"), self._nv(dispatch.get("responding_unit")))
        self._sub(eresponse, self._ns("eResponse.23"), TRANSPORT_MODE_MAP.get(disposition.get("transport_mode", ""), NV_NOT_RECORDED))
        self._sub(eresponse, self._ns("eResponse.28"), LEVEL_OF_CARE_MAP.get(disposition.get("level_of_care", ""), NV_NOT_RECORDED))

        etimes = self._sub(record, self._ns("eTimes"))
        self._sub(etimes, self._ns("eTimes.01"), self._fmt_time(dispatch.get("psap_call_time")))
        self._sub(etimes, self._ns("eTimes.03"), self._fmt_time(dispatch.get("unit_notified_time")))
        self._sub(etimes, self._ns("eTimes.05"), self._fmt_time(dispatch.get("unit_enroute_time")))
        self._sub(etimes, self._ns("eTimes.06"), self._fmt_time(dispatch.get("arrived_scene_time")))
        self._sub(etimes, self._ns("eTimes.07"), self._fmt_time(dispatch.get("patient_contact_time")))
        self._sub(etimes, self._ns("eTimes.09"), self._fmt_time(dispatch.get("departed_scene_time")))
        self._sub(etimes, self._ns("eTimes.11"), self._fmt_time(dispatch.get("arrived_destination_time")))
        self._sub(etimes, self._ns("eTimes.12"), self._fmt_time(dispatch.get("transfer_of_care_time")))

        epatient = self._sub(record, self._ns("ePatient"))
        self._sub(epatient, self._ns("ePatient.02"), self._nv(patient.get("dob")))
        self._sub(epatient, self._ns("ePatient.03"), self._nv(patient.get("last_name")))
        self._sub(epatient, self._ns("ePatient.04"), self._nv(patient.get("first_name")))
        self._sub(epatient, self._ns("ePatient.13"), GENDER_MAP.get((patient.get("gender") or "").lower(), NV_NOT_RECORDED))
        self._sub(epatient, self._ns("ePatient.14"), RACE_MAP.get((patient.get("race") or "").lower(), NV_NOT_RECORDED))
        self._sub(epatient, self._ns("ePatient.15"), self._nv(patient.get("address")))
        self._sub(epatient, self._ns("ePatient.17"), self._nv(patient.get("zip_code")))
        self._sub(epatient, self._ns("ePatient.18"), self._nv(patient.get("phone")))
        ssn = patient.get("ssn_last4")
        if ssn and str(ssn).strip():
            self._sub(epatient, self._ns("ePatient.20"), str(ssn).strip())

        esituation = self._sub(record, self._ns("eSituation"))
        self._sub(esituation, self._ns("eSituation.04"), self._nv(primary.get("chief_complaint")))
        self._sub(esituation, self._ns("eSituation.11"), self._nv(primary.get("chief_complaint")))
        medical_findings = primary.get("medical_findings", {})
        self._sub(esituation, self._ns("eSituation.13"), self._nv(medical_findings.get("acuity")) if isinstance(medical_findings, dict) else NV_NOT_RECORDED)

        ehistory = self._sub(record, self._ns("eHistory"))
        allergies = primary.get("allergies", [])
        self._sub(ehistory, self._ns("eHistory.01"), "; ".join(allergies) if allergies else NV_NOT_RECORDED)
        meds_home = primary.get("medications_home", [])
        self._sub(ehistory, self._ns("eHistory.08"), "; ".join(meds_home) if meds_home else NV_NOT_RECORDED)

        evitals = self._sub(record, self._ns("eVitals"))
        for vital in chart_dict.get("vitals", [])[:20]:
            vg = self._sub(evitals, self._ns("eVitals.VitalGroup"))
            self._sub(vg, self._ns("eVitals.01"), self._fmt_time(vital.get("recorded_at")))
            self._sub(vg, self._ns("eVitals.06"), self._nv(vital.get("systolic_bp")))
            self._sub(vg, self._ns("eVitals.07"), self._nv(vital.get("diastolic_bp")))
            self._sub(vg, self._ns("eVitals.10"), self._nv(vital.get("heart_rate")))
            self._sub(vg, self._ns("eVitals.14"), self._nv(vital.get("respiratory_rate")))
            self._sub(vg, self._ns("eVitals.16"), self._nv(vital.get("spo2")))
            self._sub(vg, self._ns("eVitals.17"), self._nv(vital.get("etco2")))
            self._sub(vg, self._ns("eVitals.18"), self._nv(vital.get("glucose")))
            self._sub(vg, self._ns("eVitals.19"), self._nv(vital.get("gcs_total")))
            self._sub(vg, self._ns("eVitals.20"), self._nv(vital.get("gcs_eye")))
            self._sub(vg, self._ns("eVitals.21"), self._nv(vital.get("gcs_verbal")))
            self._sub(vg, self._ns("eVitals.22"), self._nv(vital.get("gcs_motor")))
            self._sub(vg, self._ns("eVitals.26"), self._nv(vital.get("temperature_c")))
            self._sub(vg, self._ns("eVitals.27"), self._nv(vital.get("pain_scale")))
            self._sub(vg, self._ns("eVitals.29"), self._nv(vital.get("rhythm")))

        emedications = self._sub(record, self._ns("eMedications"))
        for med in chart_dict.get("medications", []):
            mg = self._sub(emedications, self._ns("eMedications.MedicationGroup"))
            self._sub(mg, self._ns("eMedications.03"), self._fmt_time(med.get("time_given")))
            self._sub(mg, self._ns("eMedications.04"), self._nv(med.get("medication_name")))
            self._sub(mg, self._ns("eMedications.05"), self._nv(med.get("dose")))
            self._sub(mg, self._ns("eMedications.06"), self._nv(med.get("dose_unit")))
            self._sub(mg, self._ns("eMedications.07"), self._nv(med.get("route")))
            self._sub(mg, self._ns("eMedications.10"), "9909003" if med.get("prior_to_our_care") else "9909001")

        eprocedures = self._sub(record, self._ns("eProcedures"))
        for proc in chart_dict.get("procedures", []):
            pg = self._sub(eprocedures, self._ns("eProcedures.ProcedureGroup"))
            self._sub(pg, self._ns("eProcedures.03"), self._fmt_time(proc.get("time_performed")))
            self._sub(pg, self._ns("eProcedures.05"), self._nv(proc.get("procedure_name")))
            self._sub(pg, self._ns("eProcedures.06"), str(proc.get("attempts", 1)))
            self._sub(pg, self._ns("eProcedures.07"), "9923001" if proc.get("successful") else "9923003")
            self._sub(pg, self._ns("eProcedures.08"), self._nv(proc.get("complications")))
            self._sub(pg, self._ns("eProcedures.10"), "9909003" if proc.get("prior_to_our_care") else "9909001")

        enarrative = self._sub(record, self._ns("eNarrative"))
        narrative = chart_dict.get("narrative", "")
        self._sub(enarrative, self._ns("eNarrative.01"), narrative if narrative and narrative.strip() else NV_NOT_RECORDED)

        edisposition = self._sub(record, self._ns("eDisposition"))
        self._sub(edisposition, self._ns("eDisposition.12"), self._nv(disposition.get("patient_disposition_code")))
        self._sub(edisposition, self._ns("eDisposition.16"), self._nv(disposition.get("destination_name")))
        self._sub(edisposition, self._ns("eDisposition.27"), self._nv(disposition.get("patient_disposition_code")))
        self._sub(edisposition, self._ns("eDisposition.28"), self._nv(disposition.get("transport_disposition")))

        eincident = self._sub(record, self._ns("eIncident"))
        incident_number = dispatch.get("incident_number", "")
        self._sub(eincident, self._ns("eIncident.01"), incident_number if incident_number and incident_number.strip() else NV_NOT_RECORDED)

        return tostring(root, encoding="utf-8", xml_declaration=True)
