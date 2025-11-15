from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.endpoints.user import get_current_user
from app.models.user import user_model
from app.models.volunteer import volunteer_model
from app.schemas.organization import Organization
from app.schemas.s3 import PresignedUrlResponse
from app.schemas.user import User, UserType
from app.schemas.volunteer import (
    CreateVolunteerRequest,
    TrainingDocument,
    UpdateVolunteerRequest,
    Volunteer,
)
from app.services.s3 import s3_service
from app.utils.user import verify_entity_association, verify_user_role

router = APIRouter()


@router.get("/me", response_model=Volunteer)
async def get_self(
    current_user: Annotated[User, Depends(get_current_user)],
) -> Volunteer:
    volunteer = await volunteer_model.get_volunteer_by_id(current_user.entity_id)

    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    return volunteer


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


@router.get("/me/organization/top", response_model=list[Organization])
async def get_top_organizations(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 1,
) -> list[Organization]:
    verify_user_role(current_user, UserType.VOLUNTEER)
    verify_entity_association(current_user)

    return await volunteer_model.get_top_organizations(current_user.entity_id, limit)


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


@router.get("/me/profile-picture/upload-url", response_model=PresignedUrlResponse)
async def get_profile_picture_upload_url(
    filename: str,
    filetype: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.user_type != UserType.VOLUNTEER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only volunteers can upload profile pictures",
        )

    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with a volunteer profile",
        )

    url, new_s3_key = s3_service.generate_presigned_url(
        filename,
        content_type=filetype,
        dir_prefix=f"volunteers/{current_user.entity_id}/profile",
    )

    await volunteer_model.update_volunteer_image(current_user.entity_id, new_s3_key)

    return PresignedUrlResponse(
        upload_url=url,
        file_url=new_s3_key,
    )


@router.get("/me/profile-picture")
async def get_profile_picture(
    current_user: Annotated[User, Depends(get_current_user)],
):
    image_key = await volunteer_model.get_volunteer_image_key(current_user.entity_id)
    if not image_key:
        raise HTTPException(status_code=404, detail="Profile picture not found")

    file_type = image_key.split(".")[-1]
    presigned_url = s3_service.get_presigned_url(image_key, content_type=f"image/{file_type}")
    return {"url": presigned_url}


@router.get("/{volunteer_id}/profile-picture")
async def get_volunteer_profile_picture(volunteer_id: str):
    image_key = await volunteer_model.get_volunteer_image_key(volunteer_id)
    if not image_key:
        raise HTTPException(status_code=404, detail="Profile picture not found")

    file_type = image_key.split(".")[-1]
    presigned_url = s3_service.get_presigned_url(image_key, content_type=f"image/{file_type}")
    return {"url": presigned_url}


# Generate a pre-signed URL for an event image and store the S3 key in MongoDB
@router.get("/me/upload-url", response_model=PresignedUrlResponse)
async def upload_training_document_url(
    filename: str,
    document_type: str,
    filetype: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.user_type not in [UserType.VOLUNTEER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with volunteer role can upload a training document",
        )

    # Generate the pre-signed URL
    url, new_s3_key = s3_service.generate_presigned_url(
        filename,
        content_type=filetype,
        dir_prefix=f"volunteers/{current_user.id}/training_documents",
    )
    new_training_document = TrainingDocument(file_type=document_type, image_s3_key=new_s3_key)
    updated_volunteer = UpdateVolunteerRequest(training_document=new_training_document)

    # Update the MongoDB document with the S3 key
    updated = await volunteer_model.update_volunteer(current_user.entity_id, updated_volunteer)
    if not updated:
        raise HTTPException(status_code=404, detail="Volunteer not found")

    return PresignedUrlResponse(
        upload_url=url,
        file_url=new_s3_key,
    )
