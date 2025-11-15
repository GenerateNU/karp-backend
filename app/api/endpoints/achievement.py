import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi_cache.decorator import cache

from app.api.endpoints.user import get_current_user
from app.core.cache_constants import (
    ACHIEVEMENT_IMAGES_NAMESPACE,
    VOLUNTEER_RECEIVED_ACHIEVEMENTS_NAMESPACE,
)
from app.models.achievement import achievement_model
from app.schemas.achievement import (
    Achievement,
    CreateAchievementRequest,
    UpdateAchievementRequest,
    VolunteerReceivedAchievementResponse,
)
from app.schemas.karp_event import KarpEvent
from app.schemas.s3 import PresignedUrlResponse
from app.schemas.user import User, UserType
from app.services.achievement import achievement_service
from app.services.s3 import s3_service
from app.utils.cache_key_builders import (
    achievement_images_key_builder,
    volunteer_received_achievements_key_builder,
)

logger = logging.getLogger(__name__)

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
async def get_achievements(
    event_type: Annotated[KarpEvent | None, Query()] = None,
    threshold_min: Annotated[int | None, Query()] = None,
    threshold_max: Annotated[int | None, Query()] = None,
) -> list[Achievement]:
    return await achievement_model.get_all_achievements(event_type, threshold_min, threshold_max)


@router.get("/volunteer/{volunteer_id}", response_model=list[VolunteerReceivedAchievementResponse])
@cache(
    namespace=VOLUNTEER_RECEIVED_ACHIEVEMENTS_NAMESPACE,
    expire=3600,
    key_builder=volunteer_received_achievements_key_builder,
)
async def get_achievements_by_volunteer(
    volunteer_id: str,
) -> list[VolunteerReceivedAchievementResponse]:
    return await achievement_service.get_achievements_by_volunteer(volunteer_id)


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
    await achievement_service.update_achievement(updated_achievement, achievement_id)
    return {"message": "Achievement updated successfully"}


@router.delete("/{achievement_id}", response_model=None)
async def delete_achievement(
    achievement_id: str, current_user: Annotated[User, Depends(get_current_user)]
) -> None:
    if current_user.user_type not in [UserType.ADMIN]:
        return {"message": "Only users with the admin role can delete an achievement"}
    await achievement_service.delete_achievement(achievement_id)


# Generate a pre-signed URL for an achievement image and store the S3 key in MongoDB
@router.get("/{achievement_id}/upload-url", response_model=PresignedUrlResponse)
async def get_achievement_upload_url(
    achievement_id: str,
    filename: Annotated[str, Query()],
    filetype: Annotated[str, Query()],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.user_type not in [UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with admin role can upload an achievement image",
        )

    # Verify achievement exists
    achievement = await achievement_model.get_achievement(achievement_id)
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    # Generate the pre-signed URL
    url, new_s3_key = s3_service.generate_presigned_url(
        filename, content_type=filetype, dir_prefix=f"achievements/{achievement_id}"
    )

    # Update the MongoDB document with the S3 key
    await achievement_model.update_achievement_image(achievement_id, new_s3_key)

    return PresignedUrlResponse(
        upload_url=url,
        file_url=new_s3_key,
    )


# Get an achievement image via a pre-signed URL
@router.get("/{achievement_id}/image")
@cache(
    namespace=ACHIEVEMENT_IMAGES_NAMESPACE,
    expire=60,
    key_builder=achievement_images_key_builder,
)
async def get_achievement_image(achievement_id: str):
    achievement = await achievement_model.get_achievement(achievement_id)
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    if not achievement.image_s3_key:
        raise HTTPException(status_code=404, detail="Achievement image not found")

    file_type = achievement.image_s3_key.split(".")[-1]
    presigned_url = s3_service.get_presigned_url(
        achievement.image_s3_key, content_type=f"image/{file_type}"
    )
    return {"url": presigned_url}
