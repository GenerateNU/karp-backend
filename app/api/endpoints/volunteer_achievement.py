from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.endpoints.user import get_current_admin
from app.models.volunteer import volunteer_model
from app.models.volunteer_achievement import volunteer_achievement_model
from app.schemas.user import User
from app.schemas.volunteer_achievement import (
    CreateVolunteerAchievementRequest,
    VolunteerAchievement,
)
from app.services.volunteer_achievements import volunteer_achievements_service

router = APIRouter()


@router.post("/new", response_model=VolunteerAchievement)
async def create_volunteer_achievement(
    volunteer_achievement: Annotated[CreateVolunteerAchievementRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> VolunteerAchievement:
    return await volunteer_achievements_service.create_volunteer_achievement(volunteer_achievement)


@router.get("/all", response_model=list[VolunteerAchievement])
async def get_all_volunteer_achievements() -> list[VolunteerAchievement]:

    return await volunteer_achievement_model.get_all_volunteer_achievements()


@router.get("/{volunteer_achievement_id}", response_model=VolunteerAchievement)
async def get_volunteer_achievement_by_id(
    volunteer_achievement_id: str,
) -> VolunteerAchievement:

    return await volunteer_achievement_model.get_volunteer_achievement_by_id(
        volunteer_achievement_id
    )


@router.get("/achievement/{achievement_id}", response_model=list[VolunteerAchievement])
async def get_volunteer_achievements_by_achievement_id(
    achievement_id: str,
) -> list[VolunteerAchievement]:

    return await volunteer_achievement_model.get_volunteer_achievements_by_achievement_id(
        achievement_id
    )


@router.get("/volunteer/{volunteer_id}", response_model=list[VolunteerAchievement])
async def get_volunteer_achievements_by_volunteer(volunteer_id: str) -> list[VolunteerAchievement]:
    volunteer = await volunteer_model.get_volunteer_by_id(volunteer_id)
    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    return await volunteer_achievement_model.get_volunteer_achievements_by_volunteer(volunteer_id)


@router.delete("/{volunteer_achievement_id}", response_model=VolunteerAchievement)
async def delete_volunteer_achievement(
    volunteer_achievement_id: str,
    current_user: Annotated[User, Depends(get_current_admin)],
) -> VolunteerAchievement:
    return await volunteer_achievements_service.delete_volunteer_achievement(
        volunteer_achievement_id
    )
