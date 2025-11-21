from fastapi import HTTPException

from app.models.device_token import device_token_model
from app.schemas.device_token import (
    DeviceToken,
    UnregisterDeviceTokenRequest,
)


class DeviceTokenService:
    _instance: "DeviceTokenService" = None

    def __init__(self, device_token_model=device_token_model):
        if DeviceTokenService._instance is not None:
            raise Exception("This class is a singleton!")
        self.device_token_model = device_token_model

    @classmethod
    def get_instance(cls) -> "DeviceTokenService":
        if DeviceTokenService._instance is None:
            DeviceTokenService._instance = cls()
        return DeviceTokenService._instance

    async def get_device_token_by_volunteer_id(self, volunteer_id: str) -> DeviceToken | None:
        return await self.device_token_model.get_token_by_volunteer_id(volunteer_id)

    async def get_device_tokens_by_volunteer_ids(
        self, volunteer_ids: list[str]
    ) -> list[DeviceToken]:
        device_tokens = await self.device_token_model.get_tokens_by_volunteer_ids(volunteer_ids)
        return device_tokens

    async def register_user_token(self, device_token: str, volunteer_id: str) -> DeviceToken:
        try:
            return await self.device_token_model.register_user_token(device_token, volunteer_id)
        except ValueError as err:
            raise HTTPException(status_code=400, detail="Device token already registered") from err

    async def unregister_user_token(
        self, unregister_device_token_request: UnregisterDeviceTokenRequest
    ) -> None:
        return await self.device_token_model.unregister_user_token(unregister_device_token_request)


device_token_service = DeviceTokenService.get_instance()
