import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.api.endpoints.user import get_current_admin, get_current_user
from app.models.event import event_model
from app.models.organization import org_model
from app.schemas.event import CreateEventRequest, Event, EventStatus, UpdateEventStatusRequest
from app.schemas.s3 import PresignedUrlResponse
from app.schemas.user import User, UserType
from app.services.event import event_service
from app.services.geocoding import geocoding_service
from app.services.s3 import s3_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/all", response_model=list[Event])
async def get_events() -> list[Event]:
    return await event_model.get_all_events()


@router.get("/organization/{organization_id}", response_model=list[Event])
async def get_events_by_org(organization_id: str) -> list[Event]:
    event_list = await event_model.get_events_by_organization(organization_id)
    return event_list


@router.get("/search", response_model=list[Event])
async def search_events(
    q: Annotated[str | None, Query(description="Search term (name, description, keywords)")] = None,
    sort_by: Annotated[
        Literal["start_date_time", "name", "coins", "max_volunteers", "created_at"], Query()
    ] = "start_date_time",
    sort_dir: Annotated[Literal["asc", "desc"], Query()] = "asc",
    statuses: Annotated[
        list[EventStatus] | None, Query(description="Allowed event statuses")
    ] = None,
    organization_id: Annotated[str | None, Query()] = None,
    age: Annotated[
        int | None, Query(ge=0, description="User age for eligibility filtering")
    ] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    distance_km: Annotated[float | None, Query(gt=0, le=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
) -> list[Event]:
    returned_events = await event_model.search_events(
        q=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
        statuses=statuses,
        organization_id=organization_id,
        age=age,
        lat=lat,
        lng=lng,
        distance_km=distance_km,
        page=page,
        limit=limit,
    )
    return returned_events


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
    # Non-admins must be associated to an approved organization
    if current_user.user_type != UserType.ADMIN:
        if current_user.entity_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must be associated with an organization to create an event",
            )
        organization = await org_model.get_organization_by_id(current_user.entity_id)
        if organization.status != EventStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your organization is not approved to create events",
            )

    if not event.address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Address is required to create an event",
        )

    coordinates = await geocoding_service.location_to_coordinates(event.address)

    ai_difficulty_coefficient = await event_service.estimate_event_difficulty(
        event.description or ""
    )

    return await event_model.create_event(
        event,
        current_user.id,
        current_user.entity_id,
        coordinates,
        ai_difficulty_coefficient=ai_difficulty_coefficient,
    )


@router.delete("/clear", response_model=None)
async def clear_events(
    current_user: Annotated[User, Depends(get_current_admin)],
) -> None:
    return await event_model.delete_all_events()


@router.get("/{event_id}", response_model=Event)
async def get_event_by_id(event_id: str) -> Event:
    event = await event_model.get_event_by_id(event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/{event_id}", response_model=Event | None)
async def update_event(
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
    # Admins can bypass org authorization
    if current_user.user_type != UserType.ADMIN:
        await event_service.authorize_org(event_id, current_user.entity_id)
    updated_event = await event_model.update_event(event_id, event)
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
    # Admins can bypass org authorization
    if current_user.user_type != UserType.ADMIN:
        await event_service.authorize_org(event_id, current_user.entity_id)
    return await event_model.delete_event_by_id(event_id)


# Generate a pre-signed URL for an event image and store the S3 key in MongoDB
@router.get("/{event_id}/upload-url", response_model=PresignedUrlResponse)
async def get_event_upload_url(
    event_id: str,
    filename: str,
    filetype: str,
    current_user: Annotated[User, Depends(get_current_user)],
):

    if current_user.user_type not in [UserType.ORGANIZATION, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with organization role can upload an event image",
        )

    if current_user.entity_id is None and current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with an organization to upload an event image",
        )

    # Generate the pre-signed URL
    url, new_s3_key = s3_service.generate_presigned_url(
        filename, content_type=filetype, dir_prefix=f"events/{event_id}"
    )

    # Update the MongoDB document with the S3 key
    updated = await event_service.update_event_image(event_id, new_s3_key, current_user.entity_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Event not found")

    return PresignedUrlResponse(
        upload_url=url,
        file_url=new_s3_key,
    )


# Get an event image via a pre-signed URL
@router.get("/{event_id}/image")
async def get_event_image(event_id: str):
    event = await event_model.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Image not found")
    file_type = event.image_s3_key.split(".")[-1]
    presigned_url = s3_service.get_presigned_url(
        event.image_s3_key, content_type=f"image/{file_type}"
    )
    return {"url": presigned_url}


@router.get("/{event_id}/generate-qr-code")
async def get_event_qr_codes(
    event_id: str, current_user: Annotated[User, Depends(get_current_user)]
):
    event = await event_model.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user.user_type not in [UserType.ORGANIZATION, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with organization role can get an event qr code",
        )

    if current_user.user_type != UserType.ADMIN:
        await event_service.authorize_org(event_id, current_user.entity_id)

    return await event_service.get_event_qr_codes(event)
