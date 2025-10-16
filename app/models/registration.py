from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.models.event import event_model
from app.models.volunteer import volunteer_model
from app.schemas.event import Event
from app.schemas.registration import CreateRegistrationRequest, Registration, RegistrationStatus
from app.services.volunteer import VolunteerService


class RegistrationModel:
    def __init__(self):
        self.registrations: AsyncIOMotorCollection = db["registrations"]
        self.volunteer_service = VolunteerService()

    async def get_volunteers_by_event(self, event_id: str) -> list[Registration]:
        event = await event_model.get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        registrations = await self.registrations.find({"event_id": ObjectId(event_id)}).to_list(
            length=None
        )
        return [self._to_registration(doc) for doc in registrations]

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
        return [Event(**event) for event in event_docs]

    async def create_registration(
        self, registration: CreateRegistrationRequest, volunteer_id: str
    ) -> Registration:
        event_obj_id = ObjectId(registration.event_id)
        volunteer_obj_id = ObjectId(volunteer_id)

        existing = await self.registrations.find_one(
            {"event_id": event_obj_id, "volunteer_id": volunteer_obj_id}
        )

        if existing:
            await self.registrations.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "registration_status": RegistrationStatus.UPCOMING,
                        "registered_at": datetime.now(),
                    }
                },
            )
            updated_doc = await self.registrations.find_one({"_id": existing["_id"]})
            return self._to_registration(updated_doc)

        registration_data = {
            "event_id": event_obj_id,
            "volunteer_id": volunteer_obj_id,
            "registered_at": datetime.now(),
            "registration_status": RegistrationStatus.UPCOMING,
            "clocked_in": None,
            "clocked_out": None,
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

    async def check_in_registration(self, volunteer_id: str, event_id: str) -> Registration:
        await self.registrations.update_one(
            {"volunteer_id": ObjectId(volunteer_id), "event_id": ObjectId(event_id)},
            {"$set": {"clocked_in": datetime.now()}},
        )
        updated_doc = await self.registrations.find_one(
            {"volunteer_id": ObjectId(volunteer_id), "event_id": ObjectId(event_id)}
        )
        return self._to_registration(updated_doc)

    async def check_out_registration(self, volunteer_id: str, event_id: str) -> Registration:
        event = await event_model.get_event_by_id(event_id)
        volunteer = await volunteer_model.get_volunteer_by_id(volunteer_id)
        await self.registrations.update_one(
            {"volunteer_id": ObjectId(volunteer_id), "event_id": ObjectId(event_id)},
            {"$set": {"clocked_out": datetime.now()}},
        )
        updated_doc = await self.registrations.find_one(
            {"volunteer_id": ObjectId(volunteer_id), "event_id": ObjectId(event_id)}
        )
        # Compute and persist experience/coins based on timestamps if available
        try:
            if updated_doc and updated_doc.get("clocked_in") and updated_doc.get("clocked_out"):
                duration = updated_doc["clocked_out"] - updated_doc["clocked_in"]
                exp_gained = duration.total_seconds() / 36  # 100 exp/hr
                # Update volunteer counters conservatively; ignore schema typing here
                await volunteer_model.update_volunteer(
                    volunteer_id,
                    {"experience": int(exp_gained)},  # downstream will merge incrementally
                )
                await volunteer_model.update_volunteer(volunteer_id, {"coins": event["coins"]})
                await self.volunteer_service.check_level_up(volunteer)
        except Exception:
            # Best-effort updates; do not block checkout completion
            pass
        return self._to_registration(updated_doc)

    def _to_registration(self, doc) -> Registration:
        registration_data = doc.copy()
        registration_data["id"] = str(registration_data["_id"])
        registration_data["volunteer_id"] = str(registration_data["volunteer_id"])
        registration_data["event_id"] = str(registration_data["event_id"])
        return Registration(**registration_data)


registration_model = RegistrationModel()
