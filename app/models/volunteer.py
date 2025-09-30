from typing import TYPE_CHECKING

from bson import ObjectId
from fastapi import HTTPException, status

from app.database.mongodb import db
from app.models.organization import org_model
from app.models.user import user_model
from app.schemas.organization import Organization
from app.schemas.volunteer import (
    CreateVolunteerRequest,
    EventType,
    UpdateVolunteerRequest,
    Volunteer,
)

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


class VolunteerModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["volunteers"]

    async def get_volunteer_by_id(self, volunteer_id: str) -> Volunteer:
        volunteer = await self.collection.find_one({"_id": ObjectId(volunteer_id)})
        return self._to_volunteer(volunteer) if volunteer else None

    # async def get_volunteers_by_event(self, event_id: str) -> list[Volunteer]:
    #     event = await event_model.get_event_by_id(event_id)
    #     if not event:
    #         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    #     registrations = await self.registrations.find({"eventId": ObjectId(event_id)}).to_list(
    #         length=None
    #     )
    #     volunteer_ids = [reg["volunteerId"] for reg in registrations if reg.get("volunteerId")]
    #     if not volunteer_ids:
    #         return []
    #     docs = await self.collection.find({"_id": {"$in": volunteer_ids}}).to_list(length=None)
    #     return [self._to_volunteer(d) for d in docs]

    async def get_all_volunteers(self) -> list[Volunteer]:
        volunteers_list = await self.collection.find().to_list(length=None)
        return [self._to_volunteer(volunteer) for volunteer in volunteers_list]

    async def get_top_x_volunteers(self, x: int) -> list[Volunteer]:
        volunteers_list = (
            await self.collection.find()
            .sort(
                {
                    "experience": -1,
                    "first_name": 1,
                }
            )
            .limit(x)
            .to_list()
        )
        return [self._to_volunteer(volunteer) for volunteer in volunteers_list]

    async def get_top_organizations(self, volunteer_id: str, limit: int) -> list[Organization]:
        pipeline = [
            {"$match": {"_id": volunteer_id}},
            # Get all completed registrations for volunteer
            {
                "$lookup": {
                    "from": "registrations",
                    "localField": "_id",
                    "foreignField": "volunteer_id",
                    "as": "registrations",
                }
            },
            {"$unwind": "$registrations"},
            {"$match": {"registrations.registration_status": "COMPLETED"}},
            # Get events from those registrations
            {
                "$lookup": {
                    "from": "event",
                    "localField": "event_id",
                    "foreignField": "_id",
                    "as": "event",
                }
            },
            {"$unwind": "$event"},
            # Calculate duration for each event and group by organization
            {
                "$addFields": {
                    "duration_ms": {"$subtract": ["$event.end_date_time", "$event.start_date_time"]}
                }
            },
            {
                "$group": {
                    "_id": "$event.organization_id",
                    "total_duration_ms": {"$sum": "$duration_ms"},
                }
            },
            {"$sort": {"total_duration_ms": -1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "organizations",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "organization",
                }
            },
            {"$unwind": "$organization"},
            {"$replaceRoot": {"newRoot": "$organization"}},
        ]
        results = await self.collection.aggregate(pipeline).to_list()

        return [org_model._to_organization(doc) for doc in results]

    async def create_volunteer(self, volunteer: CreateVolunteerRequest, user_id: str) -> Volunteer:
        volunteer_data = volunteer.model_dump()
        prefs = volunteer_data.get("preferences", [])
        if prefs:
            valid = {e.value for e in EventType}
            invalid = [p for p in prefs if p not in valid]
            if invalid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid preferences: {invalid}",
                )
        result = await self.collection.insert_one(volunteer_data)
        await user_model.update_entity_id_by_id(user_id, str(result.inserted_id))
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return self._to_volunteer(inserted_doc)

    async def delete_volunteer(self, volunteer_id: str):
        await self.collection.update_one(
            {"_id": ObjectId(volunteer_id)}, {"$set": {"is_active": False}}
        )

    async def update_volunteer(
        self, volunteer_id: str, volunteer: UpdateVolunteerRequest
    ) -> Volunteer:
        volunteer_data = volunteer.model_dump(exclude_unset=True)
        await self.collection.update_one({"_id": ObjectId(volunteer_id)}, {"$set": volunteer_data})
        updated_doc = await self.collection.find_one({"_id": ObjectId(volunteer_id)})
        return self._to_volunteer(updated_doc)

    def _to_volunteer(self, doc) -> Volunteer:
        volunteer_data = doc.copy()
        volunteer_data["id"] = str(volunteer_data["_id"])
        return Volunteer(**volunteer_data)


volunteer_model = VolunteerModel()
