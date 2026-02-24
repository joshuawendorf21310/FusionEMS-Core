from datetime import datetime

from pydantic import BaseModel, Field

from core_app.models.integration_registry import IntegrationProvider


class IntegrationProviderSummary(BaseModel):
    provider: IntegrationProvider
    enabled_flag: bool
    version: int
    updated_at: datetime


class IntegrationListResponse(BaseModel):
    items: list[IntegrationProviderSummary]


class IntegrationUpsertRequest(BaseModel):
    enabled_flag: bool = False
    config_json: dict = Field(default_factory=dict)
    version: int | None = None


class IntegrationEnableDisableRequest(BaseModel):
    version: int


class IntegrationResponse(BaseModel):
    provider: IntegrationProvider
    enabled_flag: bool
    version: int
    updated_at: datetime
    key_id: str


class IntegrationEventResponse(BaseModel):
    provider: IntegrationProvider
    enabled_flag: bool
    version: int
