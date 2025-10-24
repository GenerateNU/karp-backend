from fastapi import HTTPException, status

from app.models.item import item_model
from app.schemas.item import Item


class ItemService:
    def __init__(self, model=item_model):
        # Inject the model so it’s easy to mock for testing
        self.model = model

    # ensure that only the vendor who created the item can modify it
    async def authorize_vendor(self, item_id: str, vendor_id: str) -> Item | None:
        item = await self.model.get_item_by_id(item_id)
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

    async def update_item_image(self, item_id: str, s3_key: str, user_id: str) -> str:
        await self.authorize_vendor(item_id, user_id)
        updated = await item_model.update_item_image(item_id, s3_key)
        return updated
