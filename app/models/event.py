import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal

from bson import ObjectId
from fastapi import HTTPException

from app.database.mongodb import db
from app.models.volunteer import volunteer_model
from app.schemas.event import CreateEventRequest, Event, EventStatus, UpdateEventRequest
from app.schemas.location import Location
from app.schemas.registration import RegistrationStatus
from app.schemas.volunteer import Volunteer

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
            await self.collection.create_index("tags")
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
        location_radius_km: float | None = None,
        lat: float | None = None,
        lng: float | None = None,
        volunteer_event_ids: set[str] | None = None,
    ) -> list[Event]:
        # Start with base filter for published events
        filters: dict = {"status": EventStatus.PUBLISHED}

        # Filter by causes and/or qualifications (using keywords field)
        keyword_filters = []
        if causes and qualifications:
            # Require all keywords from both lists to be present
            all_keywords = list(set(causes + qualifications))
            keyword_filter = {"keywords": {"$all": all_keywords}}
            if "$and" in filters:
                filters["$and"].append(keyword_filter)
            else:
                filters = {"$and": [filters, keyword_filter]}
        elif causes:
            keyword_filter = {"keywords": {"$all": causes}}
            if "$and" in filters:
                filters["$and"].append(keyword_filter)
            else:
                filters = {"$and": [filters, keyword_filter]}
        elif qualifications:
            keyword_filter = {"keywords": {"$all": qualifications}}
            if "$and" in filters:
                filters["$and"].append(keyword_filter)
            else:
                filters = {"$and": [filters, keyword_filter]}

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

        # Move availability filtering into the MongoDB query for efficiency
        if availability_days:
            # Map day names to MongoDB $dayOfWeek numbers (1=Sunday, 2=Monday, ..., 7=Saturday)
            day_name_to_mongo = {
                "Sunday": 1,
                "Monday": 2,
                "Tuesday": 3,
                "Wednesday": 4,
                "Thursday": 5,
                "Friday": 6,
                "Saturday": 7,
            }
            mongo_weekdays = [
                day_name_to_mongo[day] for day in availability_days if day in day_name_to_mongo
            ]

            # Build $expr for day-of-week and time overlap
            expr_conditions = []
            if mongo_weekdays:
                expr_conditions.append(
                    {"$in": [{"$dayOfWeek": "$start_date_time"}, mongo_weekdays]}
                )

            # Parse time strings if provided
            if availability_start_time and availability_end_time:
                try:
                    start_hour, start_minute = map(int, availability_start_time.split(":"))
                    end_hour, end_minute = map(int, availability_end_time.split(":"))
                except (ValueError, AttributeError):
                    start_hour = start_minute = end_hour = end_minute = None

                if None not in (start_hour, start_minute, end_hour, end_minute):
                    expr_conditions.append(
                        {
                            "$and": [
                                {
                                    "$or": [
                                        {"$lt": [{"$hour": "$start_date_time"}, end_hour]},
                                        {
                                            "$and": [
                                                {"$eq": [{"$hour": "$start_date_time"}, end_hour]},
                                                {
                                                    "$lte": [
                                                        {"$minute": "$start_date_time"},
                                                        end_minute,
                                                    ]
                                                },
                                            ]
                                        },
                                    ]
                                },
                                {
                                    "$or": [
                                        {"$gt": [{"$hour": "$end_date_time"}, start_hour]},
                                        {
                                            "$and": [
                                                {"$eq": [{"$hour": "$end_date_time"}, start_hour]},
                                                {
                                                    "$gte": [
                                                        {"$minute": "$end_date_time"},
                                                        start_minute,
                                                    ]
                                                },
                                            ]
                                        },
                                    ]
                                },
                            ]
                        }
                    )

            # Add $expr to the MongoDB query
            if expr_conditions:
                if "query" not in locals():
                    query = {}
                query["$expr"] = (
                    {"$and": expr_conditions} if len(expr_conditions) > 1 else expr_conditions[0]
                )

        # Now fetch events from the database using the updated query
        # (Assume the rest of the code uses this query to fetch events)
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
                # If no volunteer_event_ids, can't sort by "been before"
                raise HTTPException(
                    status_code=400,
                    detail='volunteer_event_ids must be provided when sort_by="been_before".',
                )

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

    async def update_event(
        self, event_id: str, event: UpdateEventRequest, location: Location | None = None
    ) -> Event | None:
        event_data = await self.collection.find_one({"_id": ObjectId(event_id)})
        if event_data:
            updated_data = event.model_dump(
                mode="json", by_alias=True, exclude_unset=True, exclude={"_id", "id", "address"}
            )
            # If address was provided and geocoded, update location
            if location:
                updated_data["location"] = location.model_dump()
            await self.collection.update_one({"_id": ObjectId(event_id)}, {"$set": updated_data})
            updated_event = await self.collection.find_one({"_id": ObjectId(event_id)})

            # if event_data["status"] == Status.COMPLETED:
            #     await self.registration_service.update_not_checked_out_volunteers(event_id)

            return Event(**updated_event)
        raise HTTPException(status_code=404, detail="No event with this ID was found")

    async def delete_event_by_id(self, event_id: str) -> None:
        event = await self.collection.find_one({"_id": ObjectId(event_id)})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        await self.collection.update_one(
            {"_id": ObjectId(event_id)}, {"$set": {"status": EventStatus.CANCELLED}}
        )

    async def delete_all_events(self) -> None:
        await self.collection.update_many({}, {"$set": {"status": EventStatus.CANCELLED}})

    async def search_events(
        self,
        q: str | None = None,
        sort_by: Literal[
            "start_date_time", "name", "coins", "max_volunteers", "created_at", "distance"
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
            # Escape special regex characters to prevent invalid regex patterns
            escaped_q = re.escape(q)
            filters_q = {
                "$or": [
                    {"name": {"$regex": escaped_q, "$options": "i"}},
                    {"description": {"$regex": escaped_q, "$options": "i"}},
                    {"keywords": {"$elemMatch": {"$regex": escaped_q, "$options": "i"}}},
                ]
            }
            if filters:
                filters = {"$and": [filters, filters_q]}
            else:
                filters = filters_q

        # Filter by location using $geoNear in aggregation pipeline
        # MongoDB's $near cannot be used inside $and, so we use aggregation
        use_geo = lat is not None and lng is not None and distance_km is not None

        # Validate that distance sorting requires geo parameters
        if sort_by == "distance" and not use_geo:
            raise HTTPException(
                status_code=400,
                detail="lat, lng, and distance_km must be provided when sort_by='distance'",
            )

        if use_geo:
            location = Location(type="Point", coordinates=[lng, lat])
            max_distance_meters = int(distance_km * 1000)

            # Build aggregation pipeline
            pipeline = []

            # Stage 1: $geoNear must be first in pipeline
            geo_near_stage = {
                "$geoNear": {
                    "near": location.model_dump(),
                    "distanceField": "distance",
                    "maxDistance": max_distance_meters,
                    "spherical": True,
                    "query": filters or {},  # Apply other filters in geoNear
                }
            }
            pipeline.append(geo_near_stage)

            # Stage 2: Sort
            direction = 1 if sort_dir == "asc" else -1
            pipeline.append({"$sort": {sort_by: direction, "_id": 1}})

            # Stage 3: Skip and limit
            skip = max(0, (page - 1) * max(1, limit))
            safe_limit = max(1, min(200, limit))
            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": safe_limit})

            # Execute aggregation
            docs = await self.collection.aggregate(pipeline).to_list(length=None)
        else:
            # No location filter - use regular find
            direction = 1 if sort_dir == "asc" else -1
            skip = max(0, (page - 1) * max(1, limit))
            safe_limit = max(1, min(200, limit))
            cursor = (
                self.collection.find(filters or {})
                .sort([(sort_by, direction), ("_id", 1)])
                .skip(skip)
                .limit(safe_limit)
            )
            docs = await cursor.to_list(length=None)

        return [Event(**d) for d in docs]

    async def update_event_image(self, event_id: str, s3_key: str) -> str:
        await self.collection.update_one(
            {"_id": ObjectId(event_id)}, {"$set": {"image_s3_key": s3_key}}
        )
        return s3_key

    async def get_registered_volunteers_for_event(self, event_id: str) -> list[Volunteer]:
        pipeline = [
            {"$match": {"_id": ObjectId(event_id)}},
            {
                "$lookup": {
                    "from": "registrations",
                    "localField": "_id",
                    "foreignField": "event_id",
                    "as": "registrations",
                }
            },
            {"$unwind": "$registrations"},
            {
                "$match": {
                    "registrations.registration_status": RegistrationStatus.UPCOMING,
                }
            },
            {
                "$lookup": {
                    "from": "volunteers",
                    "localField": "registrations.volunteer_id",
                    "foreignField": "_id",
                    "as": "volunteer",
                }
            },
            {"$unwind": "$volunteer"},
            {"$replaceRoot": {"newRoot": "$volunteer"}},
        ]

        volunteer_docs = await self.collection.aggregate(pipeline).to_list(length=None)
        return [volunteer_model._to_volunteer(doc) for doc in volunteer_docs]

    async def get_events_within_next_timedelta(self, timedelta: timedelta) -> list[Event]:
        now = datetime.now(UTC)
        upper = now + timedelta

        events = await self.collection.find(
            {"start_date_time": {"$gte": now, "$lte": upper}}
        ).to_list(length=None)
        return [Event(**event) for event in events]


event_model = EventModel.get_instance()
