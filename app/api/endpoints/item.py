from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.endpoints.user import get_current_user
from app.core.enums import SortOrder
from app.models.item import ItemSortParam, item_model
from app.models.vendor import vendor_model
from app.schemas.item import CreateItemRequest, Item, ItemStatus, UpdateItemRequest
from app.schemas.s3 import PresignedUrlResponse
from app.schemas.user import User, UserType
from app.schemas.vendor import VendorStatus
from app.services.item import item_service
from app.services.s3 import s3_service

router = APIRouter()


@router.post("/new", response_model=Item)
async def post_item(
    item: Annotated[CreateItemRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Item:
    if current_user.user_type != UserType.VENDOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with vendor role can create a item",
        )

    vendor = await vendor_model.get_vendor_by_id(current_user.entity_id)
    if vendor.status != VendorStatus.APPROVED:
        print("vendor is not approved!")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your vendor is not approved to create items",
        )

    return await item_model.create_item(item, current_user.entity_id)


@router.get("/all", response_model=list[Item])
async def get_items(
    status: Annotated[ItemStatus | None, None] = None,
    search_text: str | None = None,
    vendor_id: str | None = None,
    sort_by: ItemSortParam | None = None,
    sort_order: SortOrder = SortOrder.ASC,
) -> list[Item]:
    return await item_model.get_items(status, search_text, vendor_id, sort_by, sort_order)


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: str) -> Item:
    return await item_model.get_item_by_id(item_id)


@router.put("/deactivate/{item_id}")
async def deactivate_item(item_id: str, current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.user_type != UserType.ADMIN and current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any vendor",
        )
    if current_user.user_type != UserType.ADMIN:
        await item_service.authorize_vendor(item_id, current_user.entity_id)
    await item_model.deactivate_item(item_id)
    return {"message": "Item deactivated successfully"}


@router.put("/activate/{item_id}")
async def activate_item(item_id: str, current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.user_type != UserType.ADMIN and current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any vendor",
        )
    if current_user.user_type != UserType.ADMIN:
        await item_service.authorize_vendor(item_id, current_user.entity_id)
    await item_model.activate_item(item_id)
    return {"message": "Item activated successfully"}


@router.put("/edit/{item_id}")
async def update_item(
    updated_item: Annotated[UpdateItemRequest, Body(...)],
    item_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.user_type != UserType.ADMIN and current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any vendor",
        )
    if current_user.user_type != UserType.ADMIN:
        await item_service.authorize_vendor(item_id, current_user.entity_id)
    await item_model.update_item(updated_item, item_id)
    return {"message": "Item updated successfully"}


# Generate a pre-signed URL for an event image and store the S3 key in MongoDB
@router.get("/{item_id}/upload-url", response_model=PresignedUrlResponse)
async def get_item_upload_url(
    item_id: str,
    filename: str,
    filetype: str,
    current_user: Annotated[User, Depends(get_current_user)],
):

    if current_user.user_type not in [UserType.VENDOR, UserType.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with vendor role can upload an item image",
        )

    if current_user.entity_id is None and current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with an vendor to upload an item image",
        )

    # Generate the pre-signed URL
    url, new_s3_key = s3_service.generate_presigned_url(
        filename, content_type=filetype, dir_prefix=f"items/{item_id}"
    )

    # Update the MongoDB document with the S3 key
    updated = await item_service.update_item_image(item_id, new_s3_key, current_user.entity_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Item not found")

    return PresignedUrlResponse(
        upload_url=url,
        file_url=new_s3_key,
    )


# Get an event image via a pre-signed URL
@router.get("/{item_id}/image")
async def get_item_image(item_id: str):
    item = await item_model.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Image not found")
    file_type = item.image_s3_key.split(".")[-1]
    presigned_url = s3_service.get_presigned_url(
        item.image_s3_key, content_type=f"image/{file_type}"
    )
    return {"url": presigned_url}
