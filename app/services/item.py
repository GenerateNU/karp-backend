import base64
import io
import json
import secrets

import qrcode
from fastapi import HTTPException, status

from app.models.item import item_model
from app.schemas.item import Item, UpdateItemRequest


class ItemService:
    _instance: "ItemService" = None

    def __init__(self, item_model=item_model):
        if ItemService._instance is not None:
            raise Exception("This class is a singleton!")
        self.item_model = item_model

    @classmethod
    def get_instance(cls) -> "ItemService":
        if ItemService._instance is None:
            ItemService._instance = cls()
        return ItemService._instance

    async def authorize_vendor(self, item_id: str, vendor_id: str) -> Item | None:
        item = await self.item_model.get_item_by_id(item_id)
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
        updated = await self.item_model.update_item_image(item_id, s3_key)
        return updated

    async def get_item_qr_code(self, item: Item):
        expires_at = item.expiration
        qr_token = secrets.token_hex(16)

        qr_payload = json.dumps(
            {
                "item_id": item.id,
                "qr_token": qr_token,
                "expires_at": expires_at.isoformat(),
            }
        )

        qr_data = json.dumps(qr_payload)

        qr_img = qrcode.make(qr_data)
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format="PNG")
        qr_code = base64.b64encode(qr_buf.getvalue()).decode()  # qr code image for frontend

        update_item_req = UpdateItemRequest(
            qr_code_image=qr_code,
            qr_token=qr_token,
        )

        return await self.item_model.update_item(update_item_req, item.id)


item_service = ItemService.get_instance()
