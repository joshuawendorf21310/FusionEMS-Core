import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.hems import CrewAvailability, FlightRequest, FlightRequestStatus, PagingEvent
from core_app.repositories.hems_repository import HemsRepository
from core_app.schemas.hems import (
    CrewAvailabilityCreateRequest,
    CrewAvailabilityResponse,
    FlightRequestCreateRequest,
    FlightRequestResponse,
    FlightRequestTransitionRequest,
    PagingEventCreateRequest,
    PagingEventResponse,
)

ALLOWED_TRANSITIONS = {
    FlightRequestStatus.REQUESTED: {FlightRequestStatus.ACCEPTED, FlightRequestStatus.CANCELLED},
    FlightRequestStatus.ACCEPTED: {FlightRequestStatus.ENROUTE, FlightRequestStatus.CANCELLED},
    FlightRequestStatus.ENROUTE: {FlightRequestStatus.COMPLETE, FlightRequestStatus.CANCELLED},
    FlightRequestStatus.COMPLETE: set(),
    FlightRequestStatus.CANCELLED: set(),
}


class HemsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = HemsRepository(db)

    async def create_request(self, *, tenant_id: uuid.UUID, payload: FlightRequestCreateRequest) -> FlightRequestResponse:
        req = FlightRequest(tenant_id=tenant_id, version=1, status=FlightRequestStatus.REQUESTED, accepted_by_user_id=None, patient_summary_redacted_flag=True, **payload.model_dump())
        created = await self.repo.create_request(tenant_id=tenant_id, request=req)
        await self.db.commit()
        return FlightRequestResponse.model_validate(created)

    async def list_requests(self, *, tenant_id: uuid.UUID) -> list[FlightRequestResponse]:
        return [FlightRequestResponse.model_validate(x) for x in await self.repo.list_requests(tenant_id=tenant_id)]

    async def transition_request(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, request_id: uuid.UUID, payload: FlightRequestTransitionRequest) -> FlightRequestResponse:
        req = await self._require_request(tenant_id=tenant_id, request_id=request_id)
        if req.version != payload.version:
            raise AppError(code=ErrorCodes.CONCURRENCY_CONFLICT, message="Flight request version conflict.", status_code=409, details={"server_version": req.version, "updated_at": req.updated_at.isoformat()})
        if payload.target_status not in ALLOWED_TRANSITIONS.get(req.status, set()):
            raise AppError(code=ErrorCodes.HEMS_INVALID_TRANSITION, message="Invalid flight request transition.", status_code=422)
        req.status = payload.target_status
        if payload.target_status == FlightRequestStatus.ACCEPTED:
            req.accepted_by_user_id = actor_user_id
        req.version += 1
        await self.db.flush(); await self.db.refresh(req)
        await self.db.commit()
        return FlightRequestResponse.model_validate(req)

    async def create_availability(self, *, tenant_id: uuid.UUID, payload: CrewAvailabilityCreateRequest) -> CrewAvailabilityResponse:
        entry = CrewAvailability(tenant_id=tenant_id, version=1, **payload.model_dump())
        created = await self.repo.create_availability(tenant_id=tenant_id, availability=entry)
        await self.db.commit()
        return CrewAvailabilityResponse.model_validate(created)

    async def page_request(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, request_id: uuid.UUID, payload: PagingEventCreateRequest) -> PagingEventResponse:
        await self._require_request(tenant_id=tenant_id, request_id=request_id)
        event = PagingEvent(
            tenant_id=tenant_id,
            version=1,
            flight_request_id=request_id,
            actor_user_id=actor_user_id,
            channel=payload.channel,
            delivered_at=datetime.now(UTC),
            acknowledged_at=None,
        )
        created = await self.repo.create_paging(tenant_id=tenant_id, event=event)
        await self.db.commit()
        return PagingEventResponse.model_validate(created)

    async def _require_request(self, *, tenant_id: uuid.UUID, request_id: uuid.UUID) -> FlightRequest:
        req = await self.repo.get_request(tenant_id=tenant_id, request_id=request_id)
        if req is None:
            raise AppError(code=ErrorCodes.HEMS_REQUEST_NOT_FOUND, message="Flight request not found.", status_code=404)
        return req
