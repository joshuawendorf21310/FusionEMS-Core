import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ICD10SearchItem(BaseModel):
    id: uuid.UUID
    code: str
    short_description: str
    long_description: str | None
    version: int
    updated_at: datetime


class ICD10SearchResponse(BaseModel):
    items: list[ICD10SearchItem]
    total: int


class RxNormSearchItem(BaseModel):
    id: uuid.UUID
    rxcui: str
    name: str
    tty: str | None
    version: int
    updated_at: datetime


class RxNormSearchResponse(BaseModel):
    items: list[RxNormSearchItem]
    total: int


class CodingSearchQuery(BaseModel):
    query: str = Field(min_length=2, max_length=128)
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
