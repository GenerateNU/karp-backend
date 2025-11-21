from app.database.mongodb import db
from app.schemas.device_token import (
    DeviceToken,
    UnregisterDeviceTokenRequest,
)


class DeviceTokenModel:
    _instance: "DeviceTokenModel" = None

    def __init__(self):
        if DeviceTokenModel._instance is not None:
            raise Exception("This class is a singleton!")
        self.collection = db["device_tokens"]

    @classmethod
    def get_instance(cls) -> "DeviceTokenModel":
        if DeviceTokenModel._instance is None:
            DeviceTokenModel._instance = cls()
        return DeviceTokenModel._instance

    async def get_token_by_volunteer_id(self, volunteer_id: str) -> DeviceToken | None:
        device_token = await self.collection.find_one({"volunteer_id": volunteer_id})
        return DeviceToken(**device_token) if device_token else None

    async def get_tokens_by_volunteer_ids(self, volunteer_ids: list[str]) -> list[DeviceToken]:
        device_tokens = await self.collection.find(
            {"volunteer_id": {"$in": volunteer_ids}}
        ).to_list(length=None)
        return [DeviceToken(**device_token) for device_token in device_tokens]

    async def register_user_token(
        self,
        device_token: str,
        volunteer_id: str,
    ) -> DeviceToken:
        print(device_token)
        print(volunteer_id)
        existing_token = await self.collection.find_one(
            {
                "device_token": device_token,
            }
        )
        if existing_token:
            raise ValueError("Device token already registered")

        result = await self.collection.insert_one(
            {"device_token": device_token, "volunteer_id": volunteer_id}
        )
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return DeviceToken(**inserted_doc)

    async def unregister_user_token(
        self, unregister_device_token_request: UnregisterDeviceTokenRequest
    ) -> None:
        await self.collection.delete_one(
            {
                "volunteer_id": unregister_device_token_request.volunteer_id,
            }
        )


device_token_model = DeviceTokenModel.get_instance()
