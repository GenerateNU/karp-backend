from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.endpoints.user import get_current_user
from app.models.item import item_model
from app.models.order import order_model
from app.models.volunteer import volunteer_model
from app.schemas.order import CreateOrderRequest, Order, UpdateOrderRequest
from app.schemas.user import User, UserType
from app.services.order import order_service

router = APIRouter()


@router.post("/new", response_model=Order)
async def create_order(
    order: Annotated[CreateOrderRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Order:
    if current_user.user_type != UserType.VOLUNTEER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only volunteers can place orders"
        )

    if current_user.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must be associated with a volunteer profile to place an order",
        )

    await item_model.get_item(order.item_id)
    return await order_model.create_order(order, current_user.entity_id)


@router.get("/all", response_model=list[Order])
async def get_all_orders(current_user: Annotated[User, Depends(get_current_user)]) -> list[Order]:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can view all orders"
        )
    return await order_model.get_all_orders()


@router.get("/{order_id}", response_model=Order)
async def get_order_by_id(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Order:
    return await order_service.authorize_order_access(order_id, current_user)


@router.get("/item/{item_id}", response_model=list[Order])
async def get_orders_by_item_id(
    item_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Order]:
    if current_user.user_type == UserType.VENDOR:
        item = await item_model.get_item(item_id)
        if current_user.entity_id != item.vendor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view orders for your own items",
            )
    elif current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and vendors can view orders by item",
        )

    return await order_model.get_orders_by_item_id(item_id)


@router.get("/volunteer/{volunteer_id}", response_model=list[Order])
async def get_orders_by_volunteer_id(
    volunteer_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Order]:
    volunteer = await volunteer_model.get_volunteer_by_id(volunteer_id)
    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    if current_user.user_type == UserType.VOLUNTEER:
        if current_user.entity_id != volunteer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own orders",
            )
    elif current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return await order_model.get_orders_by_volunteer_id(volunteer_id)


@router.put("/{order_id}", response_model=Order)
async def update_order_status(
    order_id: str,
    order_update: Annotated[UpdateOrderRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Order:
    await order_service.authorize_order_access(order_id, current_user)
    return await order_model.update_order_status(order_id, order_update)


@router.delete("/{order_id}", response_model=Order)
async def cancel_order(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Order:
    await order_service.authorize_order_access(order_id, current_user)
    return await order_model.cancel_order(order_id)
