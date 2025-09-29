from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.mongodb import db
from app.schemas.event import CreateEventRequest, Event, Status, UpdateEventStatusRequest
from app.schemas.data_types import Location
from app.services.event import EventService

from app.models.volunteer import volunteer_model
from app.models.user import user_model


event_service = EventService(model=None)


class EventModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["events"]

    async def create_event(self, event: CreateEventRequest, user_id: str) -> Event:
        event_data = event.model_dump(mode="json", by_alias=True, exclude={"_id", "id"})

        event_data["status"] = Status.DRAFT
        # Get the organization entity_id associated with this user
        user = await user_model.get_by_id(user_id)
        if not user or not user.entity_id:
            raise HTTPException(
                status_code=400, detail="User is not associated with an organization"
            )
        event_data["organization_id"] = user.entity_id
        event_data["created_at"] = datetime.now(UTC)
        event_data["created_by"] = user_id
        # event_data["location"] = await event_service.location_to_coordinates(event_data["address"])
        # will uncomment when we get the google maps key

        result = await self.collection.insert_one(event_data)
        event_data["_id"] = result.inserted_id
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return self.to_event(inserted_doc)

    async def get_all_events(self) -> list[Event]:
        events_list = await self.collection.find().to_list(length=None)
        return [self.to_event(event) for event in events_list]

    async def get_events_by_location(self, distance: float, location: Location) -> list[Event]:
        events_list = await self.collection.find(
            {"location": {"$near": {"$geometry": location.model_dump(), "$maxDistance": distance}}}
        ).to_list(length=None)
        return [self.to_event(event) for event in events_list]

    async def get_event_by_id(self, event_id: str) -> Event | None:
        event_data = await self.collection.find_one({"_id": ObjectId(event_id)})
        if event_data:
            return self.to_event(event_data)

        raise HTTPException(status_code=404, detail="No event with this ID was found")

    async def get_events_by_organization(self, organization_id: str) -> list[Event]:
        events_list = await self.collection.find({"organization_id": organization_id}).to_list(
            length=None
        )
        return [Event(**event) for event in events_list]

    async def update_event_status(
        self, event_id: str, event: UpdateEventStatusRequest
    ) -> Event | None:
        event_data = await self.collection.find_one({"_id": ObjectId(event_id)})
        if event_data:
            updated_data = event.model_dump(
                mode="json", by_alias=True, exclude_none=True, exclude={"_id", "id"}
            )
            await self.collection.update_one({"_id": ObjectId(event_id)}, {"$set": updated_data})
            event_data.update(updated_data)

            if event_data["Status"] == Status.COMPLETED:
                await self.update_event_status_completed(event_data)

            return self.to_event(event_data)
        raise HTTPException(status_code=404, detail="No event with this ID was found")

    async def update_event_status_completed(self, event: Event) -> None:
        duration = event["end_date_time"] - event["start_date_time"]
        exp = duration.total_seconds() / 36 # 3600 seconds in an hour * 100 exp per hour
        volunteers = await volunteer_model.get_volunteers_by_event(event["id"])
        for volunteer in volunteers:
            await volunteer_model.update_volunteer(volunteer["id"], {"exp": volunteer["exp"] + exp})
            await volunteer_model.update_volunteer(volunteer["id"], {"coins": volunteer["coins"] + event["coins"]})
            volunteer_model.check_level_up(volunteer)

    async def delete_event_by_id(self, event_id: str) -> None:
        event = await self.collection.find_one({"_id": ObjectId(event_id)})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        status = event["status"]
        if status in [Status.DRAFT, Status.COMPLETED]:
            await self.collection.update_one(
                {"_id": ObjectId(event_id)}, {"$set": {"status": Status.DELETED}}
            )
        elif status in [Status.PUBLISHED]:
            await self.collection.update_one(
                {"_id": ObjectId(event_id)}, {"$set": {"status": Status.CANCELLED}}
            )
        else:
            raise HTTPException(status_code=400, detail="Event cannot be deleted")

    async def delete_all_events(self) -> None:
        await self.collection.update_many({}, {"$set": {"status": Status.DELETED}})

    # converting id and org_id to str to display all event fields
    def to_event(self, doc) -> Event:
        event_data = doc.copy()
        event_data["id"] = str(event_data["_id"])
        event_data["organization_id"] = str(event_data["organization_id"])
        return Event(**event_data)


event_model = EventModel()
