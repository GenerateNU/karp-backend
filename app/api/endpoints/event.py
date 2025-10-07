from typing import Annotated
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, status, Query

from app.api.endpoints.user import get_current_user
from app.models.event import event_model
from app.schemas.event import CreateEventRequest, Event, UpdateEventStatusRequest
from app.schemas.data_types import Location
from app.schemas.user import User, UserType
from app.services.event import EventService

router = APIRouter()
event_service = EventService()


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


@router.get("/near", response_model=list[Event])
async def get_events_near(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    distance_km: float = Query(25, gt=0, le=200),
) -> list[Event]:
    location = Location(type="Point", coordinates=[lng, lat])
    max_distance_meters = int(distance_km * 1000)
    return await event_model.get_events_by_location(max_distance_meters, location)


@router.get("/search", response_model=list[Event])
async def search_events(
    q: str | None = Query(None, description="Search term (name, description, keywords)"),
    sort_by: Literal["start_date_time", "name", "coins", "max_volunteers"] = Query(
        "start_date_time"
    ),
    sort_dir: Literal["asc", "desc"] = Query("asc"),
    organization_id: str | None = Query(None),
    age: int | None = Query(None, ge=0, description="User age for eligibility filtering"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
) -> list[Event]:
    return await event_model.search_events(
        q=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
        organization_id=organization_id,
        age=age,
        page=page,
        limit=limit,
    )

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

    if current_user.entity_id is None and current_user.user_type != UserType.ADMIN:
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

    if current_user.entity_id is None and current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with an organization to create an event",
        )

    await event_service.authorize_org(event_id, current_user.entity_id)
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

    if current_user.entity_id is None and current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with an organization to delete an event",
        )

    await event_service.authorize_org(event_id, current_user.id)
    return await event_model.delete_event_by_id(event_id)


@router.delete("/clear", response_model=None)
async def clear_events(
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete all events",
        )
    return await event_model.delete_all_events()
