from typing import Any

from pydantic import BaseModel, Field


class AccreditationItemCreate(BaseModel):
    standard_ref: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=64)
    required_docs: list[str] = Field(default_factory=list)
    score_weight: int = Field(default=1, ge=1, le=10)


class AccreditationItemUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    required_docs: list[str] | None = None
    score_weight: int | None = None
    version: int = Field(ge=1)


class AccreditationDashboard(BaseModel):
    score_percent: float
    by_category: dict[str, Any]
    deficiencies: list[dict[str, Any]]
