from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.endpoints.user import get_current_user
from app.models.user import user_model
from app.models.volunteer import volunteer_model
from app.schemas.user import User, UserType
from app.schemas.volunteer import (
    CreateVolunteerRequest,
    UpdateVolunteerRequest,
    Volunteer,
)

router = APIRouter()


@router.get("/all", response_model=list[Volunteer])
async def get_volunteers() -> list[Volunteer]:
    return await volunteer_model.get_all_volunteers()


@router.get("/top", response_model=list[Volunteer])
async def get_top_x_volunteers(limit: int = 10) -> list[Volunteer]:
    return await volunteer_model.get_top_x_volunteers(limit)


@router.get("/{volunteer_id}", response_model=Volunteer)
async def get_volunteer_by_id(volunteer_id: str) -> Volunteer:
    volunteer = await volunteer_model.get_volunteer_by_id(volunteer_id)

    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    return volunteer


@router.post("/new", response_model=Volunteer)
async def create_volunteer(
    volunteer: Annotated[CreateVolunteerRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Volunteer:
    if current_user.user_type != UserType.VOLUNTEER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with volunteer role can create a volunteer",
        )

    if current_user.entity_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already been associated with a volunteer",
        )

    return await volunteer_model.create_volunteer(volunteer, current_user.id)


@router.put("/{volunteer_id}", response_model=Volunteer)
async def update_volunteer(
    volunteer_id: str,
    volunteer: Annotated[UpdateVolunteerRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Volunteer:
    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any volunteer",
        )

    if not await user_model.owns_entity(current_user.id, volunteer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this volunteer",
        )

    return await volunteer_model.update_volunteer(volunteer_id, volunteer)


@router.delete("/{volunteer_id}", response_model=None)
async def delete_volunteer(
    volunteer_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any volunteer",
        )

    if not await user_model.owns_entity(current_user.id, volunteer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this volunteer",
        )

    return await volunteer_model.delete_volunteer(volunteer_id)
