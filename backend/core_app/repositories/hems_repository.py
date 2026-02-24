import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.hems import CrewAvailability, FlightRequest, PagingEvent


class HemsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _tenant(tenant_id: uuid.UUID | None) -> uuid.UUID:
        if tenant_id is None:
            raise AppError(code=ErrorCodes.TENANT_SCOPE_REQUIRED, message="Tenant scope required.", status_code=400)
        return tenant_id

    async def create_request(self, *, tenant_id: uuid.UUID, request: FlightRequest) -> FlightRequest:
        request.tenant_id = self._tenant(tenant_id)
        self.db.add(request)
        await self.db.flush(); await self.db.refresh(request)
        return request

    async def get_request(self, *, tenant_id: uuid.UUID, request_id: uuid.UUID) -> FlightRequest | None:
        stmt = select(FlightRequest).where(FlightRequest.id == request_id, FlightRequest.tenant_id == self._tenant(tenant_id), FlightRequest.deleted_at.is_(None))
        return await self.db.scalar(stmt)

    async def list_requests(self, *, tenant_id: uuid.UUID) -> list[FlightRequest]:
        stmt = select(FlightRequest).where(FlightRequest.tenant_id == self._tenant(tenant_id), FlightRequest.deleted_at.is_(None))
        return list((await self.db.scalars(stmt)).all())

    async def create_availability(self, *, tenant_id: uuid.UUID, availability: CrewAvailability) -> CrewAvailability:
        availability.tenant_id = self._tenant(tenant_id)
        self.db.add(availability)
        await self.db.flush(); await self.db.refresh(availability)
        return availability

    async def create_paging(self, *, tenant_id: uuid.UUID, event: PagingEvent) -> PagingEvent:
        event.tenant_id = self._tenant(tenant_id)
        self.db.add(event)
        await self.db.flush(); await self.db.refresh(event)
        return event
