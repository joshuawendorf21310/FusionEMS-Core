from pydantic import BaseModel, EmailStr, Field

class OnboardingStartRequest(BaseModel):
    email: EmailStr
    agency_name: str = Field(min_length=2, max_length=255)
    zip_code: str = Field(min_length=3, max_length=16)
    agency_type: str = Field(pattern=r"^(EMS|Fire|HEMS)$")
    annual_call_volume: int = Field(ge=1, le=1000000)
    current_billing_percent: float = Field(ge=0.0, le=30.0)
    payer_mix: dict[str, float] = Field(default_factory=dict)
    level_mix: dict[str, float] = Field(default_factory=dict)
    selected_modules: list[str] = Field(default_factory=list)

class OnboardingStartResponse(BaseModel):
    application_id: str
    roi_snapshot_hash: str
    status: str

class ProposalResponse(BaseModel):
    application_id: str
    proposal_pdf_s3_key: str
    proposal_xlsx_s3_key: str
    roi_snapshot_hash: str
