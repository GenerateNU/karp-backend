from fastapi import HTTPException, status

from app.models.item import item_model
from app.schemas.item import Item


class ItemService:
    def __init__(self):
        pass

    # ensure that only the vendor who created the item can modify it
    async def authorize_vendor(self, item_id: str, vendor_id: str) -> Item | None:
        item = await item_model.get_item(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )
        if item.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this item",
            )


item_service = ItemService()
