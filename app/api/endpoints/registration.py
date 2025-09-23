from fastapi import APIRouter

from app.models.registration import registration_model
from app.schemas.registration import (
    Registration,
)

router = APIRouter()


# do we want to make this partiful s.t. only volunteers signed up for the event can see who going?
@router.get("/event-volunteers/{event_id}", response_model=list[Registration])
async def get_volunteers_by_event(event_id: str) -> list[Registration]:
    return await registration_model.get_volunteers_by_event(event_id)
