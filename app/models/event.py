from typing import TYPE_CHECKING, Literal

from bson import ObjectId
from fastapi import HTTPException

from app.database.mongodb import db
from app.schemas.event import CreateEventRequest, Event, EventStatus, UpdateEventStatusRequest
from app.schemas.location import Location

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


class EventModel:
    _instance: "EventModel" = None

    def __init__(self):
        if EventModel._instance is not None:
            raise Exception("This class is a singleton!")
        self.collection: AsyncIOMotorCollection = db["events"]

        self.manual_difficulty_coefficient_coefficient = 0.2

    @classmethod
    def get_instance(cls) -> "EventModel":
        if EventModel._instance is None:
            EventModel._instance = cls()
        return EventModel._instance

    async def create_indexes(self):
        try:
            await self.collection.create_index([("location", "2dsphere")])
        except Exception:
            pass

    async def create_event(
        self,
        event: CreateEventRequest,
        user_id: str,
        organization_id: str,
        location: Location,
        ai_difficulty_coefficient: float,
    ) -> Event:
        event_data = event.model_dump(mode="json", by_alias=True, exclude={"_id", "id"})
        event_data["organization_id"] = organization_id
        event_data["created_by"] = user_id
        event_data["location"] = location.model_dump()
        event_data["ai_difficulty_coefficient"] = ai_difficulty_coefficient

        difficulty_coefficient = event_data.get(
            "manual_difficulty_coefficient", 1.0
        ) * self.manual_difficulty_coefficient_coefficient + ai_difficulty_coefficient * (
            1 - self.manual_difficulty_coefficient_coefficient
        )

        event_data["difficulty_coefficient"] = difficulty_coefficient

        # Compute the max possible amount of coins earnable as
        # (end_datetime - start_datetime)[in hours] * difficulty_coefficient * 100
        coins = int(
            (event.end_date_time - event.start_date_time).total_seconds()
            / 3600
            * difficulty_coefficient
            * 100
        )
        event_data["coins"] = coins

        event = Event(**event_data)

        result = await self.collection.insert_one(
            event.model_dump(mode="json", by_alias=True, exclude={"_id", "id"})
        )
        event_data["_id"] = result.inserted_id
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return Event(**inserted_doc)

    async def get_all_events(self) -> list[Event]:
        events_list = await self.collection.find({"status": EventStatus.PUBLISHED}).to_list(
            length=None
        )
        return [Event(**event) for event in events_list]

    async def get_events_by_location(self, distance: float, location: Location) -> list[Event]:
        events_list = await self.collection.find(
            {"location": {"$near": {"$geometry": location.model_dump(), "$maxDistance": distance}}}
        ).to_list(length=None)
        return [Event(**event) for event in events_list]

    async def get_event_by_id(self, event_id: str) -> Event | None:
        event_data = await self.collection.find_one({"_id": ObjectId(event_id)})
        if event_data:
            return Event(**event_data)

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

            # if event_data["status"] == Status.COMPLETED:
            #     await self.registration_service.update_not_checked_out_volunteers(event_id)

            return Event(**event_data)
        raise HTTPException(status_code=404, detail="No event with this ID was found")

    async def delete_event_by_id(self, event_id: str) -> None:
        event = await self.collection.find_one({"_id": ObjectId(event_id)})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        status = event["status"]
        if status in [EventStatus.DRAFT, EventStatus.COMPLETED]:
            await self.collection.update_one(
                {"_id": ObjectId(event_id)}, {"$set": {"status": EventStatus.DELETED}}
            )
        elif status in [EventStatus.PUBLISHED]:
            await self.collection.update_one(
                {"_id": ObjectId(event_id)}, {"$set": {"status": EventStatus.CANCELLED}}
            )
        else:
            raise HTTPException(status_code=400, detail="Event cannot be deleted")

    async def delete_all_events(self) -> None:
        await self.collection.update_many({}, {"$set": {"status": EventStatus.DELETED}})

    async def search_events(
        self,
        q: str | None = None,
        sort_by: Literal[
            "start_date_time", "name", "coins", "max_volunteers", "created_at"
        ] = "start_date_time",
        sort_dir: Literal["asc", "desc"] = "asc",
        statuses: list[EventStatus] | None = None,
        organization_id: str | None = None,
        age: int | None = None,
        lat: float | None = None,
        lng: float | None = None,
        distance_km: float | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[Event]:
        filters: dict = {}
        if statuses:
            filters_status = {"status": {"$in": list(statuses)}}
            if filters:
                filters = {"$and": [filters, filters_status]}
            else:
                filters = filters_status

        if organization_id:
            filters["organization_id"] = organization_id

        if age is not None:
            age_clause = {
                "$and": [
                    {
                        "$or": [
                            {"age_min": {"$lte": age}},
                            {"age_min": {"$exists": False}},
                            {"age_min": None},
                        ]
                    },
                    {
                        "$or": [
                            {"age_max": {"$gte": age}},
                            {"age_max": {"$exists": False}},
                            {"age_max": None},
                        ]
                    },
                ]
            }
            if filters:
                filters = {"$and": [filters, age_clause]}
            else:
                filters = age_clause
        if q:
            filters_q = {
                "$or": [
                    {"name": {"$regex": q, "$options": "i"}},
                    {"description": {"$regex": q, "$options": "i"}},
                    {"keywords": {"$elemMatch": {"$regex": q, "$options": "i"}}},
                ]
            }
            if filters:
                filters = {"$and": [filters, filters_q]}
            else:
                filters = filters_q

        if lat is not None and lng is not None and distance_km is not None:
            location = Location(type="Point", coordinates=[lng, lat])
            max_distance_meters = int(distance_km * 1000)
            filters["location"] = {
                "$near": {"$geometry": location.model_dump(), "$maxDistance": max_distance_meters}
            }

        direction = 1 if sort_dir == "asc" else -1
        skip = max(0, (page - 1) * max(1, limit))
        cursor = (
            self.collection.find(filters or {})
            .sort([(sort_by, direction), ("_id", 1)])
            .skip(skip)
            .limit(max(1, min(200, limit)))
        )
        docs = await cursor.to_list(length=None)

        return [Event(**d) for d in docs]

    async def update_event_image(self, event_id: str, s3_key: str) -> str:
        await self.collection.update_one(
            {"_id": ObjectId(event_id)}, {"$set": {"image_s3_key": s3_key}}
        )
        return s3_key


event_model = EventModel.get_instance()
