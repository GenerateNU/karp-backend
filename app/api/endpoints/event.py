from typing import Annotated

from fastapi import APIRouter, Body

from app.models.event import event_model
from app.schemas.event import CreateEventRequest, Event, UpdateEventStatusRequestDTO

router = APIRouter()


@router.put("/new", response_model=Event)
async def create_event(event: Annotated[CreateEventRequest, Body(...)]) -> Event:
    return await event_model.create_event(event)


@router.post("/{event_id}", response_model=Event | None)
async def update_event_status(
    event_id: str, event: Annotated[UpdateEventStatusRequestDTO, Body(...)]
) -> Event | None:
    updated_event = await event_model.update_event_status(event_id, event)
    return updated_event


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


@router.delete("/{event_id}", response_model=None)
async def clear_event_by_id(event_id: str) -> None:
    return await event_model.delete_event_by_id(event_id)


# Deletes all Events -- Not Sure if we need
# @router.delete("/clear", response_model=None)
# async def clear_events() -> None:
#     return await event_model.delete_all_events()
