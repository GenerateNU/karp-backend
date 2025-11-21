from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.api.endpoints.user import get_current_user
from app.schemas.device_token import (
    CreateDeviceTokenRequest,
    DeviceToken,
    UnregisterDeviceTokenRequest,
)
from app.schemas.user import User
from app.services.device_token import device_token_service

router = APIRouter()


@router.post("/register", response_model=DeviceToken)
async def register_device_token(
    device_token_request: Annotated[CreateDeviceTokenRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return await device_token_service.register_user_token(
        device_token_request.device_token, current_user.entity_id
    )


@router.delete("/unregister", response_model=None)
async def unregister_device_token(current_user: Annotated[User, Depends(get_current_user)]):
    await device_token_service.unregister_user_token(
        UnregisterDeviceTokenRequest(volunteer_id=current_user.entity_id)
    )
    return {"detail": "Successfully unregistered device token"}
