from typing import TYPE_CHECKING

from app.database.mongodb import db
from app.models.user import user_model
from app.schemas.user import Volunteer
from app.schemas.volunteer import CreateVolunteerRequest, UpdateVolunteerRequest

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


class VolunteerModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["volunteer"]
        self.registrations: AsyncIOMotorCollection = db["volunteer_registratons"]

    async def get_volunteer_by_id(self, volunteer_id: str) -> Volunteer:
        volunteer = self.collection.find_one({"id": id})
        if volunteer:
            return self._to_volunteer(volunteer)
        return None

    async def get_volunteers_by_event(self, event_id: str) -> list[Volunteer]:
        registrations = await self.registrations.find({"eventId": event_id}).to_list(length=None)
        volunteer_ids = [reg["volunteerId"] for reg in registrations if reg.get("volunteerId")]
        if not volunteer_ids:
            return []
        docs = await self.collection.find({"_id": {"$in": volunteer_ids}}).to_list(length=None)
        return [self._to_volunteer(d) for d in docs]

    async def get_all_volunteers(self) -> list[Volunteer]:
        volunteers_list = await self.collection.find().to_list(length=None)
        return [self._to_volunteer(volunteer) for volunteer in volunteers_list]

    async def create_volunteer(self, volunteer: CreateVolunteerRequest, user_id: str) -> Volunteer:
        volunteer_data = volunteer.model_dump()
        result = await self.collection.insert_one(volunteer_data)
        await user_model.update_entity_id_by_id(user_id, str(result.inserted_id))
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return self._to_volunteer(inserted_doc)

    async def delete_volunteer(self, volunteer_id: str):
        await self.collection.update_one({"_id": volunteer_id}, {"$set": {"isActive": False}})

    async def update_volunteer(
        self, volunteer_id: str, volunteer: UpdateVolunteerRequest
    ) -> Volunteer:
        volunteer_data = volunteer.model_dump(exclude_unset=True)
        await self.collection.update_one({"id": volunteer_id}, {"$set": volunteer_data})
        updated_doc = await self.collection.find_one({"_id": volunteer_id})
        return self._to_volunteer(updated_doc)

    def _to_volunteer(self, doc) -> Volunteer:
        volunteer_data = doc.copy()
        volunteer_data["id"] = str(volunteer_data["_id"])
        return Volunteer(**volunteer_data)


volunteer_model = VolunteerModel()
