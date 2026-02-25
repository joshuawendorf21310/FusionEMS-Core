from pydantic import BaseModel, Field
from typing import Any

class FhirExportRequest(BaseModel):
    entity_type: str = Field(pattern=r"^(patient|incident|call|fire_report)$")
    entity_id: str

class FhirExportResponse(BaseModel):
    artifact_id: str
    resource_type: str
    resource: dict[str, Any]
