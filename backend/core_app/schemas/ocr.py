import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.ocr import OcrSourceType


class OcrPresignRequest(BaseModel):
    filename: str


class OcrPresignResponse(BaseModel):
    upload_url: str
    object_key: str


class OcrUploadRegisterRequest(BaseModel):
    incident_id: uuid.UUID
    source_type: OcrSourceType
    s3_object_key: str
    image_sha256: str
    extracted_json: dict
    confidence_score: float = Field(ge=0, le=1)
    model_version: str


class OcrApproveRequest(BaseModel):
    version: int = Field(ge=1)


class OcrApplyRequest(BaseModel):
    version: int = Field(ge=1)
    selected_fields: dict
    applied_to_entity_type: str
    applied_to_entity_id: uuid.UUID


class OcrUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    incident_id: uuid.UUID
    source_type: OcrSourceType
    confidence_score: float
    model_version: str
    approved_flag: bool
    version: int
    created_at: datetime


class OcrProposedChangesResponse(BaseModel):
    upload_id: uuid.UUID
    approved_flag: bool
    selected_fields: dict
