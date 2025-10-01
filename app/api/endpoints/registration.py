from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.endpoints.user import get_current_user
from app.models.registration import registration_model
from app.models.volunteer import volunteer_model
from app.schemas.event import Event
from app.schemas.registration import Registration, RegistrationStatus
from app.schemas.user import User, UserType

router = APIRouter()


# do we want to make this partiful s.t. only volunteers signed up for the event can see who going?
@router.get("/event-volunteers/{event_id}", response_model=list[Registration])
async def get_volunteers_by_event(event_id: str) -> list[Registration]:
    return await registration_model.get_volunteers_by_event(event_id)


@router.get("/events/{volunteer_id}", response_model=list[Event])
async def get_events_by_volunteer(
    volunteer_id: str,
    status: Annotated[RegistrationStatus | None, Query(description="Filter by status")] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> list[Event]:
    volunteer = await volunteer_model.get_volunteer_by_id(volunteer_id)
    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    if current_user.user_type == UserType.VOLUNTEER:
        if current_user.entity_id != volunteer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own events",
            )
    elif current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return await registration_model.get_events_by_volunteer(volunteer_id, status)
