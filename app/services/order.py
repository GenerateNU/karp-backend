from fastapi import HTTPException, status

from app.models.item import item_model
from app.models.order import order_model
from app.schemas.order import Order
from app.schemas.user import User, UserType


class OrderService:
    def __init__(self, model=order_model):
        self.model = model

    async def authorize_order_access(self, order_id: str, current_user: User) -> Order:
        order = await self.model.get_order_by_id(order_id)

        if current_user.user_type == UserType.VOLUNTEER:
            if current_user.entity_id != order.volunteer_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access your own orders",
                )
        elif current_user.user_type == UserType.VENDOR:
            item = await item_model.get_item(order.item_id)
            if current_user.entity_id != item.vendor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access orders for your own items",
                )
        elif current_user.user_type != UserType.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return order
