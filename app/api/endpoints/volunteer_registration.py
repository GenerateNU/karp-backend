from fastapi import APIRouter

from app.models.volunteer_registration import volunteer_registration_model
from app.schemas.volunteer_registration import (
    VolunteerRegistration,
)

router = APIRouter()


# do we want to make this partiful s.t. only volunteers signed up for the event can see who going?
@router.get("/event-volunteers/{event_id}", response_model=list[VolunteerRegistration])
async def get_volunteers_by_event(event_id: str) -> list[VolunteerRegistration]:
    return await volunteer_registration_model.get_volunteers_by_event(event_id)
