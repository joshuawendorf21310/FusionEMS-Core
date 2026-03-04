from __future__ import annotations

import uuid
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring


NEMSIS_NS = "http://www.nemsis.org"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


class NEMSISXMLBuilder:
    def __init__(self, nemsis_version: str = "3.5.0.211008CP3"):
        self._version = nemsis_version

    def build_ems_dataset(self, record: dict) -> str:
        root = Element("EMSDataSet")
        root.set("xmlns", NEMSIS_NS)
        root.set("xmlns:xsi", XSI_NS)

        header = SubElement(root, "Header")
        dem_group = SubElement(header, "DemographicGroup")
        self._add_text(dem_group, "dAgency.01", record.get("agency_state_id", ""))
        self._add_text(dem_group, "dAgency.02", record.get("agency_number", ""))
        self._add_text(dem_group, "dAgency.04", record.get("agency_state", "48"))

        patient_care = SubElement(header, "PatientCareReport")
        self._add_text(patient_care, "eRecord.01", record.get("record_id", str(uuid.uuid4())))
        sw_group = SubElement(patient_care, "eRecord.SoftwareApplicationGroup")
        self._add_text(sw_group, "eRecord.02", "FusionEMS Quantum")
        self._add_text(sw_group, "eRecord.03", self._version)
        self._add_text(sw_group, "eRecord.04", "FusionEMS")

        self._build_eresponse(patient_care, record)
        self._build_etimes(patient_care, record)
        self._build_epatient(patient_care, record)
        self._build_esituation(patient_care, record)
        self._build_edisposition(patient_care, record)
        self._build_evitals(patient_care, record)
        self._build_escene(patient_care, record)

        xml_str = tostring(root, encoding="unicode", xml_declaration=False)
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

    def build_dem_dataset(self, agency: dict) -> str:
        root = Element("DEMDataSet")
        root.set("xmlns", NEMSIS_NS)
        root.set("xmlns:xsi", XSI_NS)

        header = SubElement(root, "Header")
        self._add_text(header, "DemographicReport", "")

        dem_group = SubElement(header, "dAgency")
        self._add_text(dem_group, "dAgency.01", agency.get("state_id", ""))
        self._add_text(dem_group, "dAgency.02", agency.get("number", ""))
        self._add_text(dem_group, "dAgency.03", agency.get("name", ""))
        self._add_text(dem_group, "dAgency.04", agency.get("state_code", ""))

        xml_str = tostring(root, encoding="unicode", xml_declaration=False)
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

    def _build_eresponse(self, parent: Element, record: dict) -> None:
        section = SubElement(parent, "eResponse")
        self._add_text(section, "eResponse.01", record.get("ems_agency_number", ""))
        self._add_text(section, "eResponse.05", record.get("type_of_service", ""))
        self._add_text(section, "eResponse.07", record.get("primary_role", ""))
        self._add_text(section, "eResponse.13", record.get("unit_transport_capability", ""))
        self._add_text(section, "eResponse.23", record.get("response_mode", ""))

    def _build_etimes(self, parent: Element, record: dict) -> None:
        section = SubElement(parent, "eTimes")
        times = record.get("times", {})
        self._add_text(section, "eTimes.01", times.get("psap_call", ""))
        self._add_text(section, "eTimes.03", times.get("unit_notified", ""))
        self._add_text(section, "eTimes.05", times.get("unit_en_route", ""))
        self._add_text(section, "eTimes.06", times.get("unit_arrived_scene", ""))
        self._add_text(section, "eTimes.07", times.get("arrived_patient", ""))
        self._add_text(section, "eTimes.09", times.get("unit_left_scene", ""))
        self._add_text(section, "eTimes.11", times.get("arrived_destination", ""))
        self._add_text(section, "eTimes.13", times.get("unit_back_in_service", ""))

    def _build_epatient(self, parent: Element, record: dict) -> None:
        section = SubElement(parent, "ePatient")
        patient = record.get("patient", {})
        self._add_text(section, "ePatient.02", patient.get("last_name", ""))
        self._add_text(section, "ePatient.03", patient.get("first_name", ""))
        self._add_text(section, "ePatient.13", patient.get("gender", ""))
        self._add_text(section, "ePatient.15", patient.get("race", ""))
        self._add_text(section, "ePatient.16", patient.get("age", ""))
        self._add_text(section, "ePatient.17", patient.get("age_units", ""))

    def _build_esituation(self, parent: Element, record: dict) -> None:
        section = SubElement(parent, "eSituation")
        self._add_text(section, "eSituation.01", record.get("complaint_reported", ""))
        self._add_text(section, "eSituation.07", record.get("primary_symptom", ""))
        self._add_text(section, "eSituation.09", record.get("primary_impression", ""))
        self._add_text(section, "eSituation.11", record.get("provider_primary_impression", ""))

    def _build_edisposition(self, parent: Element, record: dict) -> None:
        section = SubElement(parent, "eDisposition")
        self._add_text(section, "eDisposition.12", record.get("disposition", ""))
        self._add_text(section, "eDisposition.17", record.get("transport_disposition", ""))
        self._add_text(section, "eDisposition.19", record.get("final_patient_acuity", ""))
        self._add_text(section, "eDisposition.21", record.get("reason_no_transport", ""))

    def _build_evitals(self, parent: Element, record: dict) -> None:
        vitals_list = record.get("vitals", [])
        for v in vitals_list:
            group = SubElement(parent, "eVitals.VitalGroup")
            self._add_text(group, "eVitals.01", v.get("datetime", ""))
            signs = SubElement(group, "eVitals.BloodPressureGroup")
            self._add_text(signs, "eVitals.06", v.get("sbp", ""))
            self._add_text(signs, "eVitals.07", v.get("dbp", ""))
            self._add_text(group, "eVitals.10", v.get("heart_rate", ""))
            self._add_text(group, "eVitals.12", v.get("pulse_oximetry", ""))
            self._add_text(group, "eVitals.14", v.get("respiratory_rate", ""))
            self._add_text(group, "eVitals.24", v.get("gcs_total", ""))

    def _build_escene(self, parent: Element, record: dict) -> None:
        section = SubElement(parent, "eScene")
        scene = record.get("scene", {})
        self._add_text(section, "eScene.01", scene.get("first_crew_on_scene", ""))
        self._add_text(section, "eScene.09", scene.get("incident_location_type", ""))
        self._add_text(section, "eScene.15", scene.get("incident_street", ""))
        self._add_text(section, "eScene.17", scene.get("incident_city", ""))
        self._add_text(section, "eScene.18", scene.get("incident_state", ""))
        self._add_text(section, "eScene.19", scene.get("incident_zip", ""))

    @staticmethod
    def _add_text(parent: Element, tag: str, text: str) -> None:
        if text:
            el = SubElement(parent, tag)
            el.text = str(text)
