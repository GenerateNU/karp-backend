from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.models.event import event_model
from app.schemas.volunteer_registration import (
    VolunteerRegistration,
)


class VolunteerRegistrationModel:
    def __init__(self):
        self.registrations: AsyncIOMotorCollection = db["volunteer_registrations"]

    async def get_volunteers_by_event(self, event_id: str) -> list[VolunteerRegistration]:
        event = await event_model.get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        print(event)

        pipeline = [
            {
                "$match": {"event_id": ObjectId(event_id)}
            },  # filters the entries that have this event id
            {
                # joins with memberships tables
                "$lookup": {
                    "from": "memberships",  # join memberships
                    "localField": "volunteer_id",  # volunteer id in volunteer_registrations
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
        print(volunteers_docs[0])
        return [self._to_volunteer(volunteer) for volunteer in volunteers_docs]

    def _to_volunteer(self, doc) -> VolunteerRegistration:
        volunteer_reg_data = doc.copy()
        volunteer_reg_data["id"] = str(volunteer_reg_data["_id"])
        volunteer_reg_data["volunteer_id"] = str(volunteer_reg_data["volunteer_id"])
        return VolunteerRegistration(**volunteer_reg_data)


volunteer_registration_model = VolunteerRegistrationModel()
