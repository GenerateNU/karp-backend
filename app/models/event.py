from datetime import UTC, datetime, time
from typing import TYPE_CHECKING, Literal

from bson import ObjectId
from fastapi import HTTPException

from app.database.mongodb import db
from app.models.user import user_model
from app.schemas.event import CreateEventRequest, Event, Status, UpdateEventStatusRequest
from app.schemas.location import Location

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


class EventModel:
    _instance: "EventModel" = None

    def __init__(self):
        if EventModel._instance is not None:
            raise Exception("This class is a singleton!")
        self.collection: AsyncIOMotorCollection = db["events"]

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
        self, event: CreateEventRequest, user_id: str, location: Location
    ) -> Event:
        event_data = event.model_dump(mode="json", by_alias=True, exclude={"_id", "id"})

        event_data["status"] = Status.PUBLISHED
        # Get the organization entity_id associated with this user
        user = await user_model.get_by_id(user_id)
        if not user or not user.entity_id:
            raise HTTPException(
                status_code=400, detail="User is not associated with an organization"
            )
        event_data["organization_id"] = user.entity_id
        event_data["created_at"] = datetime.now(UTC)
        event_data["created_by"] = user_id
        event_data["location"] = location.model_dump()

        result = await self.collection.insert_one(event_data)
        event_data["_id"] = result.inserted_id
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return Event(**inserted_doc)

    async def get_all_events(
        self,
        sort_by: (
            Literal["been_before", "new_additions", "coins_low_to_high", "coins_high_to_low"] | None
        ) = None,
        causes: list[str] | None = None,
        qualifications: list[str] | None = None,
        availability_days: list[str] | None = None,
        availability_start_time: str | None = None,
        availability_end_time: str | None = None,
        location_city: str | None = None,
        location_state: str | None = None,
        location_radius_km: float | None = None,
        lat: float | None = None,
        lng: float | None = None,
        volunteer_event_ids: set[str] | None = None,
    ) -> list[Event]:
        # Start with base filter for published events
        filters: dict = {"status": Status.PUBLISHED}

        # Filter by causes (using keywords field)
        if causes:
            cause_filter = {"keywords": {"$in": causes}}
            if "$and" in filters:
                filters["$and"].append(cause_filter)
            else:
                filters = {"$and": [filters, cause_filter]}

        # Filter by qualifications (using keywords field)
        if qualifications:
            qual_filter = {"keywords": {"$in": qualifications}}
            if "$and" in filters:
                filters["$and"].append(qual_filter)
            else:
                filters = {"$and": [filters, qual_filter]}

        # Filter by availability (days and times)
        # Note: We'll filter in Python after fetching, as MongoDB date filtering with $expr
        # can be complex and we need to check day of week and time ranges

        # Filter by location
        # Note: $near must be the first condition, so we handle it separately
        location_query = None
        if lat and lng and location_radius_km:
            location = Location(type="Point", coordinates=[lng, lat])
            max_distance_meters = int(location_radius_km * 1000)
            location_query = {
                "location": {
                    "$near": {
                        "$geometry": location.model_dump(),
                        "$maxDistance": max_distance_meters,
                    }
                }
            }

        # Build final query - if location filter exists, combine with other filters
        # Note: $near must be in the query, but we can combine it with $and
        if location_query:
            if "$and" in filters:
                # Flatten: add location_query to existing $and array
                final_filters = {"$and": filters["$and"] + [location_query]}
            else:
                final_filters = {"$and": [filters, location_query]}
        else:
            final_filters = filters

        # Get all events matching filters
        events_cursor = self.collection.find(final_filters)
        events_list = await events_cursor.to_list(length=None)
        events = [Event(**event) for event in events_list]

        # Apply availability filter in Python (more flexible for day/time matching)
        if availability_days:
            day_to_weekday = {
                "Sunday": 6,
                "Monday": 0,
                "Tuesday": 1,
                "Wednesday": 2,
                "Thursday": 3,
                "Friday": 4,
                "Saturday": 5,
            }
            weekday_numbers = {
                day_to_weekday[day] for day in availability_days if day in day_to_weekday
            }

            # Parse time strings if provided
            start_time_obj = None
            end_time_obj = None
            if availability_start_time:
                try:
                    hour, minute = map(int, availability_start_time.split(":"))
                    start_time_obj = time(hour, minute)
                except (ValueError, AttributeError):
                    pass

            if availability_end_time:
                try:
                    hour, minute = map(int, availability_end_time.split(":"))
                    end_time_obj = time(hour, minute)
                except (ValueError, AttributeError):
                    pass

            # Filter events by day and time
            filtered_events = []
            for event in events:
                # Python weekday(): 0=Monday, 1=Tuesday, ..., 6=Sunday
                # Our mapping: Sunday=6, Monday=0, Tuesday=1, ..., Saturday=5
                event_weekday = event.start_date_time.weekday()
                # Convert: if weekday is 6 (Sunday), keep as 6; otherwise keep as is
                event_weekday_num = 6 if event_weekday == 6 else event_weekday

                if event_weekday_num in weekday_numbers:
                    # Check time if provided
                    if start_time_obj and end_time_obj:
                        event_start_time = event.start_date_time.time()
                        event_end_time = event.end_date_time.time()
                        # Check if event time overlaps with availability window
                        # Event overlaps if: event starts before availability ends AND event ends after availability starts
                        if event_start_time <= end_time_obj and event_end_time >= start_time_obj:
                            filtered_events.append(event)
                    else:
                        # No time filter, just check day
                        filtered_events.append(event)

            events = filtered_events

        # Handle "been before" filter - requires volunteer_event_ids from endpoint
        if sort_by == "been_before" and volunteer_event_ids is not None:
            # Separate events into "been before" and "not been before"
            been_before = [e for e in events if e.id in volunteer_event_ids]
            not_been_before = [e for e in events if e.id not in volunteer_event_ids]

            # Sort: been before first, then not been before
            events = been_before + not_been_before

        # Apply sorting
        if sort_by == "new_additions":
            events.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_by == "coins_low_to_high":
            events.sort(key=lambda x: x.coins)
        elif sort_by == "coins_high_to_low":
            events.sort(key=lambda x: x.coins, reverse=True)
        elif sort_by == "been_before":
            # Already sorted above if volunteer_event_ids provided
            if volunteer_event_ids is None:
                # If no volunteer_event_ids, can't sort by "been before", so sort by date
                events.sort(key=lambda x: x.start_date_time)

        return events

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

    async def search_events(
        self,
        q: str | None = None,
        sort_by: Literal["start_date_time", "name", "coins", "max_volunteers"] = "start_date_time",
        sort_dir: Literal["asc", "desc"] = "asc",
        statuses: list[Status] | None = None,
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
            try:
                filters["organization_id"] = ObjectId(organization_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid organization_id") from None

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

        if lat and lng and distance_km:
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
