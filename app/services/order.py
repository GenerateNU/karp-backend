from fastapi import HTTPException, status

from app.models.item import item_model
from app.models.order import order_model
from app.models.volunteer import volunteer_model
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
            item = await item_model.get_item_by_id(order.item_id)
            if current_user.entity_id != item.vendor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access orders for your own items",
                )
        elif current_user.user_type != UserType.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return order

    async def validate_and_process_order(self, item_id: str, volunteer_id: str) -> None:
        item = await item_model.get_item(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        # Get the volunteer to check their coins
        volunteer = await volunteer_model.get_volunteer_by_id(volunteer_id)
        if not volunteer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

        # Check if volunteer has enough coins
        if volunteer.coins < item.price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient coins. Required: {item.price}, Available: {volunteer.coins}",
            )

        # Deduct coins from volunteer
        new_coin_balance = volunteer.coins - item.price
        await volunteer_model.update_volunteer(volunteer_id, {"coins": new_coin_balance})
