from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.mongodb import db
from app.schemas.event import CreateEventRequest, Event, Status, UpdateEventStatusRequest
from app.schemas.data_types import Location
from app.services.context import ServiceContext
from app.models.volunteer import volunteer_model
from app.models.user import user_model


class EventModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["events"]

    async def create_event(self, event: CreateEventRequest, user_id: str) -> Event:
        event_data = event.model_dump(mode="json", by_alias=True, exclude={"_id", "id"})

        event_data["status"] = Status.DRAFT
        # Get the organization entity_id associated with this user
        user = await user_model.get_by_id(user_id)
        if not user or not user.entity_id:
            raise HTTPException(
                status_code=400, detail="User is not associated with an organization"
            )
        event_data["organization_id"] = user.entity_id
        event_data["created_at"] = datetime.now(UTC)
        event_data["created_by"] = user_id
        # event_data["location"] = (await event_service.location_to_coordinates(event_data["address"])).model_dump()
        # will uncomment when we get the google maps key

        result = await self.collection.insert_one(event_data)
        event_data["_id"] = result.inserted_id
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})
        return self.to_event(inserted_doc)

    async def get_all_events(self) -> list[Event]:
        events_list = await self.collection.find().to_list(length=None)
        return [self.to_event(event) for event in events_list]

    async def get_events_by_location(self, distance: float, location: Location) -> list[Event]:
        events_list = await self.collection.find(
            {"location": {"$near": {"$geometry": location.model_dump(), "$maxDistance": distance}}}
        ).to_list(length=None)
        return [self.to_event(event) for event in events_list]

    async def get_event_by_id(self, event_id: str) -> Event | None:
        event_data = await self.collection.find_one({"_id": ObjectId(event_id)})
        if event_data:
            return self.to_event(event_data)

        raise HTTPException(status_code=404, detail="No event with this ID was found")

    async def get_events_by_organization(self, organization_id: str) -> list[Event]:
        events_list = await self.collection.find({"organization_id": organization_id}).to_list(
            length=None
        )
        return [Event(**event) for event in events_list]

    async def update_event_status(
        self, event_id: str, event: UpdateEventStatusRequest, ctx: ServiceContext
    ) -> Event | None:
        event_data = await self.collection.find_one({"_id": ObjectId(event_id)})
        if event_data:
            updated_data = event.model_dump(
                mode="json", by_alias=True, exclude_none=True, exclude={"_id", "id"}
            )
            await self.collection.update_one({"_id": ObjectId(event_id)}, {"$set": updated_data})
            event_data.update(updated_data)

            if event_data["status"] == Status.COMPLETED:
                await self.mark_event_completed(event_id, event_data, ctx)

            return self.to_event(event_data)
        raise HTTPException(status_code=404, detail="No event with this ID was found")

    async def mark_event_completed(
        self, event_id: str, event_data: dict, ctx: ServiceContext
    ) -> None:
        """Mark event as completed and handle volunteer rewards"""
        # Get volunteers for this event
        from app.models.registration import registration_model

        volunteers = await registration_model.get_volunteers_by_event(event_id)

        # Calculate EXP reward
        exp_reward = ctx.need_event().calculate_exp_reward(
            event_data["start_date_time"], event_data["end_date_time"]
        )

        # Update volunteers who haven't checked out
        to_update = await ctx.need_registration().bulk_checkout_missing(volunteers)

        for volunteer in to_update:
            # Update clocked_out time
            await registration_model.update_registration(
                volunteer["id"], {"clocked_out": volunteer["clocked_out"]}
            )

            # Add EXP and coins
            await volunteer_model.update_volunteer(
                volunteer["volunteer_id"], {"exp": volunteer.get("exp", 0) + exp_reward}
            )
            await volunteer_model.update_volunteer(
                volunteer["volunteer_id"],
                {"coins": volunteer.get("coins", 0) + event_data["coins"]},
            )

            # Check for level up
            updated_volunteer = await volunteer_model.get_volunteer_by_id(volunteer["volunteer_id"])
            if ctx.need_volunteer().should_level_up(updated_volunteer):
                new_level = ctx.need_volunteer().get_new_level(updated_volunteer)
                await volunteer_model.update_volunteer(
                    volunteer["volunteer_id"], {"level": new_level}
                )

                # Add achievement if needed
                if ctx.need_volunteer_achievements().should_add_achievement(
                    volunteer["volunteer_id"], new_level
                ):
                    achievement_id = ctx.need_volunteer_achievements().get_level_achievement_id(
                        new_level
                    )
                    achievement_data = ctx.need_volunteer_achievements().create_achievement_request(
                        volunteer["volunteer_id"], achievement_id
                    )
                    from app.models.volunteer_achievement import volunteer_achievement_model

                    await volunteer_achievement_model.create_volunteer_achievement(achievement_data)

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

    # converting id and org_id to str to display all event fields
    def to_event(self, doc) -> Event:
        event_data = doc.copy()
        event_data["id"] = str(event_data["_id"])
        event_data["organization_id"] = str(event_data["organization_id"])
        return Event(**event_data)


event_model = EventModel()
