import uuid
from datetime import datetime

from pydantic import BaseModel


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
