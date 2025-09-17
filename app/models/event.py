from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.schemas.event import CreateEventRequest, Event, UpdateEventStatusRequestDTO


class EventModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["events"]

    async def create_event(self, event: CreateEventRequest) -> Event:
        event_data = event.model_dump()

        await self.collection.insert_one(event_data)

        return Event(**event_data)

    async def get_all_events(self) -> list[Event]:
        events_list = await self.collection.find().to_list(length=None)

        return [Event(**event) for event in events_list]

    async def get_event_by_id(self, event_id: str) -> Event | None:
        event_data = await self.collection.find_one({"_id": event_id})
        if event_data:
            return Event(**event_data)
        return None

    async def get_events_by_organization(self, organization_id: str) -> list[Event]:
        events_list = await self.collection.find({"organizationID": organization_id}).to_list(
            length=None
        )
        return [Event(**event) for event in events_list]

    async def update_event_status(
        self, event_id: str, event: UpdateEventStatusRequestDTO
    ) -> Event | None:
        event_data = await self.collection.find_one({"_id": event_id})
        if event_data:
            updated_data = event.model_dump()
            await self.collection.update_one({"_id": event_id}, {"$set": updated_data})
            event_data.update(updated_data)
            return Event(**event_data)
        return None

    async def delete_event_by_id(self, event_id: str) -> None:
        await self.collection.delete_one({"_id": event_id})

    async def delete_all_events(self) -> None:
        await self.collection.delete_many({})


event_model = EventModel()
