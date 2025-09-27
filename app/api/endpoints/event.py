from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.endpoints.user import get_current_user
from app.models.event import event_model
from app.schemas.event import CreateEventRequest, Event, UpdateEventStatusRequest
from app.schemas.user import User, UserType
from app.services.event import EventService

router = APIRouter()
event_service = EventService(event_model)


@router.get("/all", response_model=list[Event])
async def get_events() -> list[Event]:
    return await event_model.get_all_events()


@router.get("/{event_id}", response_model=Event | None)
async def get_event_by_id(event_id: str) -> Event | None:
    event = await event_model.get_event_by_id(event_id)
    return event


@router.get("/organization/{organization_id}", response_model=list[Event])
async def get_events_by_org(organization_id: str) -> list[Event]:
    event_list = await event_model.get_events_by_organization(organization_id)
    return event_list


@router.post("/new", response_model=Event)
async def create_event(
    event: Annotated[CreateEventRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Event:
    if current_user.user_type not in [UserType.ORGANIZATION, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with organization role can create an event",
        )

    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with an organization to create an event",
        )

    return await event_model.create_event(event, current_user.id)


@router.put("/{event_id}", response_model=Event | None)
async def update_event_status(
    event_id: str,
    event: Annotated[UpdateEventStatusRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Event | None:

    if current_user.user_type not in [UserType.ORGANIZATION, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with organization role can create an event",
        )

    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with an organization to create an event",
        )

    await event_service.authorize_org(event_id, current_user.id)
    updated_event = await event_model.update_event_status(event_id, event)
    return updated_event


@router.delete("/{event_id}", response_model=None)
async def clear_event_by_id(
    event_id: str, current_user: Annotated[User, Depends(get_current_user)]
) -> None:
    if current_user.user_type not in [UserType.ORGANIZATION, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with organization role can delete an event",
        )

    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with an organization to delete an event",
        )

    await event_service.authorize_org(event_id, current_user.id)
    return await event_model.delete_event_by_id(event_id)


@router.delete("/clear", response_model=None)
async def clear_events() -> None:
    return await event_model.delete_all_events()
