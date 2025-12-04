import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from bson import ObjectId
from fastapi import HTTPException, status

from app.database.mongodb import db
from app.models.user import user_model
from app.schemas.organization import Organization
from app.schemas.volunteer import (
    CreateVolunteerRequest,
    EventType,
    TrainingDocument,
    UpdateVolunteerRequest,
    Volunteer,
)

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection

logger = logging.getLogger(__name__)


class VolunteerModel:
    _instance: "VolunteerModel" = None

    def __init__(self):
        if VolunteerModel._instance is not None:
            raise Exception("This class is a singleton!")
        self.collection: AsyncIOMotorCollection = db["volunteers"]

    @classmethod
    def get_instance(cls) -> "VolunteerModel":
        if VolunteerModel._instance is None:
            VolunteerModel._instance = cls()
        return VolunteerModel._instance

    async def create_indexes(self) -> None:
        try:
            await self.collection.create_index("preferences")
            logger.info("Volunteer recommendation indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating volunteer indexes: {e}")

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

        return [Organization(**doc) for doc in results]

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
        result = await self.collection.insert_one(Volunteer(**volunteer_data).model_dump())
        await user_model.update_entity_id_by_id(user_id, str(result.inserted_id))
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return self._to_volunteer(inserted_doc)

    async def delete_volunteer(self, volunteer_id: str):
        await self.collection.update_one(
            {"_id": ObjectId(volunteer_id)}, {"$set": {"is_active": False}}
        )

    async def update_volunteer_image(self, volunteer_id: str, s3_key: str) -> str:
        await self.collection.update_one(
            {"_id": ObjectId(volunteer_id)}, {"$set": {"image_s3_key": s3_key}}
        )
        return s3_key

    async def get_volunteer_image_key(self, volunteer_id: str) -> str | None:
        volunteer = await self.collection.find_one(
            {"_id": ObjectId(volunteer_id)}, {"image_s3_key": 1}
        )
        return volunteer.get("image_s3_key") if volunteer else None

    async def update_volunteer(
        self, volunteer_id: str, volunteer: UpdateVolunteerRequest
    ) -> Volunteer:
        existing_volunteer = await self.get_volunteer_by_id(volunteer_id)
        volunteer_data = volunteer.model_dump(exclude_unset=True)

        updated_data = {}
        curr_training_docs = []

        # retrieving and converting existing training documents from volunteer
        for td in existing_volunteer.training_documents:
            if isinstance(td, TrainingDocument):
                curr_training_docs.append(td.model_dump())
            else:
                curr_training_docs.append(td)

        # appending new training document to exisitng documents
        if "training_document" in volunteer_data:
            new_training_doc = volunteer_data.pop("training_document")
            curr_training_docs.append(TrainingDocument(**new_training_doc).model_dump())

        updated_data = {**volunteer_data, "training_documents": curr_training_docs}

        await self.collection.update_one({"_id": ObjectId(volunteer_id)}, {"$set": updated_data})
        updated_doc = await self.collection.find_one({"_id": ObjectId(volunteer_id)})
        return self._to_volunteer(updated_doc)

    def _to_volunteer(self, doc) -> Volunteer:
        volunteer_data = doc.copy()
        volunteer_data["id"] = str(volunteer_data["_id"])

        # Handle missing birth_date - convert from age if present, otherwise use default
        if "birth_date" not in volunteer_data:
            if "age" in volunteer_data:
                # Calculate birth_date from age (assume current year)
                age = volunteer_data.pop("age")
                birth_date = datetime.now() - timedelta(days=age * 365)
                volunteer_data["birth_date"] = birth_date
            else:
                # Default to 25 years ago if neither birth_date nor age is present
                volunteer_data["birth_date"] = datetime.now() - timedelta(days=25 * 365)

        # Handle missing list fields - default to empty list
        for field in ["qualifications", "preferred_days", "preferences"]:
            volunteer_data.setdefault(field, [])
        training_docs = volunteer_data.get("training_documents", [])

        # converting dicts into TrainingDocuments objects
        volunteer_data["training_documents"] = [
            td if isinstance(td, TrainingDocument) else TrainingDocument(**td)
            for td in training_docs
        ]
        return Volunteer(**volunteer_data)


volunteer_model = VolunteerModel.get_instance()
