from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.endpoints.user import get_current_user
from app.models.achievement import achievement_model
from app.schemas.achievement import Achievement, CreateAchievementRequest, UpdateAchievementRequest
from app.schemas.user import User, UserType
from app.services.achievement import AchievementService

router = APIRouter()
achievement_service = AchievementService(achievement_model)


@router.post("/new", response_model=Achievement)
async def post_achievement(
    achievement: Annotated[CreateAchievementRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Achievement:
    if current_user.user_type != UserType.VENDOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with vendor role can create a achievement",
        )

    return await achievement_model.create_achievement(achievement, current_user.id)


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

    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any vendor",
        )

    await achievement_service.authorize_vendor(achievement_id, current_user.id)
    await achievement_model.deactivate_achievement(achievement_id)
    return {"message": "Achievement deactivated successfully"}


@router.put("/activate/{achievement_id}")
async def activate_achievement(
    achievement_id: str, current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any vendor",
        )

    await achievement_service.authorize_vendor(achievement_id, current_user.id)
    await achievement_model.activate_achievement(achievement_id)
    return {"message": "Achievement activated successfully"}


@router.put("/edit/{achievement_id}")
async def update_achievement(
    updated_achievement: Annotated[UpdateAchievementRequest, Body(...)],
    achievement_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any vendor",
        )

    await achievement_service.authorize_vendor(achievement_id, current_user.id)
    await achievement_model.update_achievement(updated_achievement, achievement_id)
    return {"message": "Achievement updated successfully"}
