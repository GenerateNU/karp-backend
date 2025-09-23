from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.endpoints.users import get_current_user
from app.models.item import item_model
from app.schemas.item import CreateItemRequest, Item, UpdateItemRequest
from app.schemas.user import User, UserType
from app.services.item import ItemService

router = APIRouter()
item_service = ItemService(item_model)


@router.post("/new", response_model=Item)
async def post_item(
    item: Annotated[CreateItemRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Item:

    print(current_user.user_type)
    if current_user.user_type != UserType.VENDOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with vendor role can create a item",
        )

    return await item_model.create_item(item, current_user.id)


@router.get("/all", response_model=list[Item])
async def get_items() -> list[Item]:
    return await item_model.get_all_items()


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: str) -> Item:
    return await item_model.get_item(item_id)


@router.put("/deactivate/{item_id}")
async def deactivate_item(item_id: str, current_user: Annotated[User, Depends(get_current_user)]):

    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any vendor",
        )

    await item_service.authorize_vendor(item_id, current_user.id)
    await item_model.deactivate_item(item_id)
    return {"message": "Item deactivated successfully"}


@router.put("/activate/{item_id}")
async def activate_item(item_id: str, current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any vendor",
        )

    await item_service.authorize_vendor(item_id, current_user.id)
    await item_model.activate_item(item_id)
    return {"message": "Item activated successfully"}


@router.put("/edit/{item_id}")
async def update_item(
    updated_item: Annotated[UpdateItemRequest, Body(...)],
    item_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any vendor",
        )

    await item_service.authorize_vendor(item_id, current_user.id)
    await item_model.update_item(updated_item, item_id)
    return {"message": "Item updated successfully"}
