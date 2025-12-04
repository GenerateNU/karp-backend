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
        q: str | None = None,
        sort_by: (
            Literal[
                "been_before",
                "new_additions",
                "coins_low_to_high",
                "coins_high_to_low",
                "distance",
                "start_date_time",
                "name",
                "coins",
                "max_volunteers",
                "created_at",
            ]
            | None
        ) = None,
        sort_dir: Literal["asc", "desc"] = "desc",
        statuses: list[EventStatus] | None = None,
        organization_id: str | None = None,
        age: int | None = None,
        page: int = 1,
        limit: int = 200,
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
        filters: dict = {}
        if statuses:
            filters_status = {"status": {"$in": list(statuses)}}
            if filters:
                filters = {"$and": [filters, filters_status]}
            else:
                filters = filters_status
        else:
            filters = {"status": EventStatus.APPROVED}

        if organization_id:
            if filters:
                if "$and" in filters:
                    filters["$and"].append({"organization_id": organization_id})
                else:
                    filters = {"$and": [filters, {"organization_id": organization_id}]}
            else:
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
                if "$and" in filters:
                    filters["$and"].append(age_clause)
                else:
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
                if "$and" in filters:
                    filters["$and"].append(filters_q)
                else:
                    filters = {"$and": [filters, filters_q]}
            else:
                filters = filters_q

        # Filter by causes and/or qualifications (using keywords field)
        if causes and qualifications:
            all_keywords = list(set(causes + qualifications))
            keyword_filter = {"keywords": {"$all": all_keywords}}
            if filters:
                if "$and" in filters:
                    filters["$and"].append(keyword_filter)
                else:
                    filters = {"$and": [filters, keyword_filter]}
            else:
                filters = keyword_filter
        elif causes:
            keyword_filter = {"keywords": {"$all": causes}}
            if filters:
                if "$and" in filters:
                    filters["$and"].append(keyword_filter)
                else:
                    filters = {"$and": [filters, keyword_filter]}
            else:
                filters = keyword_filter
        elif qualifications:
            keyword_filter = {"keywords": {"$all": qualifications}}
            if filters:
                if "$and" in filters:
                    filters["$and"].append(keyword_filter)
                else:
                    filters = {"$and": [filters, keyword_filter]}
            else:
                filters = keyword_filter

        # Apply availability filtering
        if availability_days:
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

            expr_conditions = []
            if mongo_weekdays:
                expr_conditions.append(
                    {"$in": [{"$dayOfWeek": "$start_date_time"}, mongo_weekdays]}
                )

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

            if expr_conditions:
                expr_filter = {
                    "$expr": (
                        {"$and": expr_conditions}
                        if len(expr_conditions) > 1
                        else expr_conditions[0]
                    )
                }
                if filters:
                    if "$and" in filters:
                        filters["$and"].append(expr_filter)
                    else:
                        filters = {"$and": [filters, expr_filter]}
                else:
                    filters = expr_filter

        use_geo = lat is not None and lng is not None and location_radius_km is not None

        if sort_by == "distance" and not use_geo:
            raise HTTPException(
                status_code=400,
                detail="lat, lng, and location_radius_km must be provided when sort_by='distance'",
            )

        if sort_by == "been_before":
            if volunteer_event_ids is None:
                raise HTTPException(
                    status_code=400,
                    detail='volunteer_event_ids must be provided when sort_by="been_before".',
                )
            # For "been_before", we need to fetch all events first, then sort in Python
            # because MongoDB can't easily sort by "in set" vs "not in set"
            if use_geo:
                location = Location(type="Point", coordinates=[lng, lat])
                max_distance_meters = int(location_radius_km * 1000)
                pipeline = []
                geo_near_stage = {
                    "$geoNear": {
                        "near": location.model_dump(),
                        "distanceField": "distance",
                        "maxDistance": max_distance_meters,
                        "spherical": True,
                        "query": filters or {},
                    }
                }
                pipeline.append(geo_near_stage)
                docs = await self.collection.aggregate(pipeline).to_list(length=None)
            else:
                cursor = self.collection.find(filters or {})
                docs = await cursor.to_list(length=None)

            events = [Event(**d) for d in docs]
            been_before = [e for e in events if e.id in volunteer_event_ids]
            not_been_before = [e for e in events if e.id not in volunteer_event_ids]
            events = been_before + not_been_before

            # Apply pagination
            skip = max(0, (page - 1) * max(1, limit))
            safe_limit = max(1, min(200, limit))
            events = events[skip : skip + safe_limit]
            return events

        # For other sort types, use database-level sorting/pagination (matching search_events)
        if use_geo:
            location = Location(type="Point", coordinates=[lng, lat])
            max_distance_meters = int(location_radius_km * 1000)

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
            # Map sort_by to MongoDB field names
            sort_field_map = {
                "new_additions": "created_at",
                "created_at": "created_at",
                "coins_low_to_high": "coins",
                "coins_high_to_low": "coins",
                "coins": "coins",
                "start_date_time": "start_date_time",
                "name": "name",
                "max_volunteers": "max_volunteers",
                "distance": "distance",
            }
            # Default to start_date_time if no sort_by (matching search_events default)
            mongo_sort_field = (
                sort_field_map.get(sort_by, sort_by) if sort_by else "start_date_time"
            )
            direction = 1 if sort_dir == "asc" else -1

            # Special handling for coins_low_to_high (reverse direction)
            if sort_by == "coins_low_to_high":
                direction = 1
            elif sort_by == "coins_high_to_low":
                direction = -1

            pipeline.append({"$sort": {mongo_sort_field: direction, "_id": 1}})

            # Stage 3: Skip and limit
            skip = max(0, (page - 1) * max(1, limit))
            safe_limit = max(1, min(200, limit))
            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": safe_limit})

            # Execute aggregation
            docs = await self.collection.aggregate(pipeline).to_list(length=None)
        else:
            # No location filter - use regular find with database-level sort/pagination
            sort_field_map = {
                "new_additions": "created_at",
                "created_at": "created_at",
                "coins_low_to_high": "coins",
                "coins_high_to_low": "coins",
                "coins": "coins",
                "start_date_time": "start_date_time",
                "name": "name",
                "max_volunteers": "max_volunteers",
            }
            mongo_sort_field = (
                sort_field_map.get(sort_by, sort_by) if sort_by else "start_date_time"
            )
            direction = 1 if sort_dir == "asc" else -1

            if sort_by == "coins_low_to_high":
                direction = 1
            elif sort_by == "coins_high_to_low":
                direction = -1

            skip = max(0, (page - 1) * max(1, limit))
            safe_limit = max(1, min(200, limit))
            cursor = (
                self.collection.find(filters or {})
                .sort([(mongo_sort_field, direction), ("_id", 1)])
                .skip(skip)
                .limit(safe_limit)
            )
            docs = await cursor.to_list(length=None)

        events = [Event(**d) for d in docs]

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
