from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.schemas.event import CreateEventRequest, Event, Status, UpdateEventStatusRequestDTO


class EventModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["events"]

    async def create_event(self, event: CreateEventRequest) -> Event:
        ev = Event(
            **event.model_dump(),
            status=Status.DRAFT,
            created_at=datetime.now(UTC),
        )
        doc = ev.model_dump(mode="json", by_alias=True, exclude={"_id", "id"})
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return Event(**doc)

    async def get_all_events(self) -> list[Event]:
        events_list = await self.collection.find().to_list(length=None)
        return [Event(**event) for event in events_list]

    async def get_event_by_id(self, event_id: str) -> Event | None:
        event_data = await self.collection.find_one({"_id": ObjectId(event_id)})
        return Event(**event_data) if event_data else None

    async def get_events_by_organization(self, organization_id: str) -> list[Event]:
        events_list = await self.collection.find({"organization_id": organization_id}).to_list(
            length=None
        )
        return [Event(**event) for event in events_list]

    async def update_event_status(
        self, event_id: str, event: UpdateEventStatusRequestDTO
    ) -> Event | None:
        event_data = await self.collection.find_one({"_id": ObjectId(event_id)})
        if event_data:
            updated_data = event.model_dump(
                mode="json", by_alias=True, exclude_none=True, exclude={"_id", "id"}
            )
            await self.collection.update_one({"_id": ObjectId(event_id)}, {"$set": updated_data})
            event_data.update(updated_data)
            return Event(**event_data)
        raise HTTPException(status_code=404, detail="No event with this ID was found")
        return None

    async def delete_event_by_id(self, event_id: str) -> None:
        await self.collection.delete_one({"_id": ObjectId(event_id)})

    async def delete_all_events(self) -> None:
        await self.collection.delete_many({})


event_model = EventModel()
