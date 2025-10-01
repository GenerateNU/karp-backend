from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.api.endpoints.user import get_current_user
from app.models.achievement import achievement_model
from app.schemas.achievement import Achievement, CreateAchievementRequest, UpdateAchievementRequest
from app.schemas.user import User, UserType

router = APIRouter()


@router.post("/new", response_model=Achievement)
async def post_achievement(
    achievement: Annotated[CreateAchievementRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.user_type not in [UserType.ADMIN]:
        return {"message": "Only users with the admin role can create an achievement"}
    return await achievement_model.create_achievement(achievement)


@router.get("/all", response_model=list[Achievement])
async def get_achievements() -> list[Achievement]:
    return await achievement_model.get_all_achievements()


@router.get("/{achievement_id}", response_model=Achievement)
async def get_achievement(achievement_id: str) -> Achievement:
    return await achievement_model.get_achievement(achievement_id)


@router.put("/deactivate/{achievement_id}")
async def deactivate_achievement(
    achievement_id: str, current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.user_type not in [UserType.ADMIN]:
        return {"message": "Only users with the admin role can deactivate an achievement"}
    return {"message": "Achievement deactivated successfully"}


@router.put("/activate/{achievement_id}")
async def activate_achievement(
    achievement_id: str, current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.user_type not in [UserType.ADMIN]:
        return {"message": "Only users with the admin role can activate an achievement"}
    await achievement_model.activate_achievement(achievement_id)
    return {"message": "Achievement activated successfully"}


@router.put("/edit/{achievement_id}")
async def update_achievement(
    updated_achievement: Annotated[UpdateAchievementRequest, Body(...)],
    achievement_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.user_type not in [UserType.ADMIN]:
        return {"message": "Only users with the admin role can update an achievement"}
    await achievement_model.update_achievement(updated_achievement, achievement_id)
    return {"message": "Achievement updated successfully"}


@router.delete("/{achievement_id}", response_model=None)
async def delete_achievement(
    achievement_id: str, current_user: Annotated[User, Depends(get_current_user)]
) -> None:
    if current_user.user_type not in [UserType.ADMIN]:
        return {"message": "Only users with the admin role can delete an achievement"}
    return await achievement_model.delete_achievement(achievement_id)
