from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.api.endpoints.user import get_current_user
from app.models.registration import registration_model
from app.models.volunteer import volunteer_model
from app.models.event import event_model
from app.schemas.event import Event
from app.schemas.registration import CreateRegistrationRequest, Registration, RegistrationStatus
from app.schemas.user import User, UserType
from app.services.volunteer import VolunteerService

router = APIRouter()
volunteer_service = VolunteerService()

# do we want to make this partiful s.t. only volunteers signed up for the event can see who going?
@router.get("/event-volunteers/{event_id}", response_model=list[Registration])
async def get_volunteers_by_event(event_id: str) -> list[Registration]:
    return await registration_model.get_volunteers_by_event(event_id)


@router.get("/events/{volunteer_id}", response_model=list[Event])
async def get_events_by_volunteer(
    volunteer_id: str,
    registration_status: Annotated[
        RegistrationStatus | None, Query(description="Filter by status")
    ] = None,
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

    return await registration_model.get_events_by_volunteer(volunteer_id, registration_status)


@router.post("/new", response_model=Registration)
async def create_registrion(
    registration: Annotated[CreateRegistrationRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Registration:
    if current_user.user_type != UserType.VOLUNTEER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only volunteers can register for events"
        )

    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with a volunteer profile to register for an event",
        )

    return await registration_model.create_registration(registration, current_user.entity_id)


@router.put("/unregister/{registration_id}", response_model=Registration)
async def unregister_registration(
    registration_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Registration:
    if current_user.user_type != UserType.VOLUNTEER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only volunteers can unregister from events",
        )

    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with a volunteer profile to unregister from an event",
        )

    return await registration_model.unregister_registration(registration_id, current_user.entity_id)


@router.put("/check-in/{volunteer_id}", response_model=Registration)
async def check_in_registration(
    event_id: str,
    volunteer_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Registration:

    if current_user.user_type not in [UserType.ORGANIZATION, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organizations can check in volunteers",
        )

    volunteer = await volunteer_model.get_volunteer_by_id(volunteer_id)
    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    return await registration_model.check_in_registration(volunteer_id, event_id)


@router.put("/check-out/{volunteer_id}", response_model=Registration)
async def check_out_registration(
    event_id: str,
    volunteer_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Registration:

    if current_user.user_type not in [UserType.ORGANIZATION, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organizations can check out volunteers",
        )

    volunteer = await volunteer_model.get_volunteer_by_id(volunteer_id)
    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    event = await event_model.get_event_by_id(event_id)
    registration = await registration_model.check_out_registration(volunteer_id, event_id)
    await volunteer_service.handle_volunteer_checkout_rewards(registration, volunteer_id, event, volunteer)

    return registration
