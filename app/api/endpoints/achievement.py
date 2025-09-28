from typing import Annotated

from fastapi import APIRouter, Body

from app.models.achievement import achievement_model
from app.schemas.achievement import Achievement, CreateAchievementRequest, UpdateAchievementRequest

router = APIRouter()


@router.post("/new", response_model=Achievement)
async def post_achievement(achievement: Annotated[CreateAchievementRequest, Body(...)]):
    return await achievement_model.create_achievement(achievement)


@router.get("/all", response_model=list[Achievement])
async def get_achievements() -> list[Achievement]:
    return await achievement_model.get_all_achievements()


@router.get("/{achievement_id}", response_model=Achievement)
async def get_achievement(achievement_id: str) -> Achievement:
    return await achievement_model.get_achievement(achievement_id)


@router.put("/deactivate/{achievement_id}")
async def deactivate_achievement(achievement_id: str):
    await achievement_model.deactivate_achievement(achievement_id)
    return {"message": "Achievement deactivated successfully"}


@router.put("/activate/{achievement_id}")
async def activate_achievement(achievement_id: str):
    await achievement_model.activate_achievement(achievement_id)
    return {"message": "Achievement activated successfully"}


@router.put("/edit/{achievement_id}")
async def update_achievement(
    updated_achievement: Annotated[UpdateAchievementRequest, Body(...)],
    achievement_id: str,
):

    await achievement_model.update_achievement(updated_achievement, achievement_id)
    return {"message": "Achievement updated successfully"}


@router.delete("/{achievement_id}", response_model=None)
async def delete_achievement(achievement_id: str) -> None:

    return await achievement_model.delete_achievement(achievement_id)
