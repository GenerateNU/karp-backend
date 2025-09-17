from typing import Annotated

from fastapi import APIRouter, Body

from app.models.item import item_model
from app.schemas.item import CreateItemRequest, Item, UpdateItemRequest

router = APIRouter()


@router.post("/{vendor_id}", response_model=Item)
async def post_item(item: Annotated[CreateItemRequest, Body(...)], vendor_id: str) -> Item:
    return await item_model.create_item(item, vendor_id)


@router.get("/all", response_model=list[Item])
async def get_items() -> list[Item]:
    return await item_model.get_all_items()


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: str) -> Item:
    return await item_model.get_item(item_id)


@router.put("/{item_id}/deactivate")
async def deactivate_item(item_id: str):
    await item_model.deactivate_item(item_id)
    return {"message": "Item deactivated successfully"}


@router.put("/{item_id}/activate")
async def activate_item(item_id: str):
    await item_model.activate_item(item_id)
    return {"message": "Item activated successfully"}


@router.put("/{item_id}")
async def update_item(updated_item: Annotated[UpdateItemRequest, Body(...)], item_id: str):
    await item_model.update_item(updated_item, item_id)
    return {"message": "Item updated successfully"}
