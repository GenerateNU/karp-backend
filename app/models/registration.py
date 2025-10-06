from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.models.event import event_model
from app.schemas.event import Event
from app.schemas.registration import CreateRegistrationRequest, Registration, RegistrationStatus


class RegistrationModel:
    def __init__(self):
        self.registrations: AsyncIOMotorCollection = db["registrations"]

    async def get_volunteers_by_event(self, event_id: str) -> list[Registration]:
        event = await event_model.get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        pipeline = [
            {
                "$match": {"event_id": ObjectId(event_id)}
            },  # filters the entries that have this event id
            {
                # joins with memberships tables
                "$lookup": {
                    "from": "memberships",  # join memberships
                    "localField": "volunteer_id",  # volunteer id in registrations
                    "foreignField": "entity_id",  # entity_id in memberships
                    "as": "membership_docs",
                }
            },
            {
                "$unwind": "$membership_docs"
            },  # results are converted from a joined array to a single document
            {
                "$project": {
                    "_id": 1,  # returns only the fields we want
                    "volunteer_id": "$volunteer_id",
                    "first_name": "$membership_docs.first_name",
                    "last_name": "$membership_docs.last_name",
                    "username": "$membership_docs.username",
                }
            },
        ]

        volunteers_docs = await self.registrations.aggregate(pipeline).to_list(length=None)
        return [self._to_volunteer(volunteer) for volunteer in volunteers_docs]

    async def get_events_by_volunteer(
        self, volunteer_id: str, status: RegistrationStatus | None
    ) -> list[Event]:
        match_stage: dict = {"volunteer_id": ObjectId(volunteer_id)}
        if status is not None:
            match_stage["registration_status"] = status

        pipeline = [
            {"$match": match_stage},
            {
                "$lookup": {
                    "from": "events",
                    "localField": "event_id",
                    "foreignField": "_id",
                    "as": "event_docs",
                }
            },
            {"$unwind": "$event_docs"},
            {"$replaceRoot": {"newRoot": "$event_docs"}},
        ]
        event_docs = await self.registrations.aggregate(pipeline).to_list(length=None)
        return [event_model.to_event(event) for event in event_docs]

    async def create_registration(
        self, registration: CreateRegistrationRequest, volunteer_id: str
    ) -> Registration:
        registration_data = {
            "event_id": ObjectId(registration.event_id),
            "volunteer_id": ObjectId(volunteer_id),
            "registered_at": datetime.now(),
            "registration_status": RegistrationStatus.UPCOMING,
            "clocked_in": False,
            "clocked_out": False,
        }

        result = await self.registrations.insert_one(registration_data)
        inserted_doc = await self.registrations.find_one({"_id": result.inserted_id})

        return self._to_registration(inserted_doc)

    async def unregister_registration(
        self, registration_id: str, volunteer_id: str
    ) -> Registration:
        registration = await self.registrations.find_one({"_id": ObjectId(registration_id)})

        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found"
            )

        if str(registration["volunteer_id"]) != volunteer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to unregister from this event",
            )

        await self.registrations.update_one(
            {"_id": ObjectId(registration_id)},
            {"$set": {"registration_status": RegistrationStatus.UNREGISTERED}},
        )
        updated_doc = await self.registrations.find_one({"_id": ObjectId(registration_id)})
        return self._to_registration(updated_doc)

    def _to_registration(self, doc) -> Registration:
        registration_data = doc.copy()
        registration_data["id"] = str(registration_data["_id"])
        registration_data["volunteer_id"] = str(registration_data["volunteer_id"])
        registration_data["event_id"] = str(registration_data["event_id"])
        return Registration(**registration_data)


registration_model = RegistrationModel()
