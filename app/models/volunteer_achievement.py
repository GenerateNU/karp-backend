from typing import TYPE_CHECKING

from bson import ObjectId
from fastapi import HTTPException

from app.database.mongodb import db
from app.schemas.achievement import VolunteerReceivedAchievementResponse
from app.schemas.volunteer_achievement import (
    CreateVolunteerAchievementRequest,
    VolunteerAchievement,
)
from app.utils.object_id import parse_object_id

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


class VolunteerAchievementModel:
    _instance: "VolunteerAchievementModel" = None

    def __init__(self):
        if VolunteerAchievementModel._instance is not None:
            raise Exception("This class is a singleton!")
        self.collection: AsyncIOMotorCollection = db["volunteerAchievements"]

    @classmethod
    def get_instance(cls) -> "VolunteerAchievementModel":
        if VolunteerAchievementModel._instance is None:
            VolunteerAchievementModel._instance = cls()
        return VolunteerAchievementModel._instance

    async def create_volunteer_achievement(
        self, volunteer_achievement: CreateVolunteerAchievementRequest
    ) -> VolunteerAchievement:
        volunteer_achievement_data = {
            "achievement_id": ObjectId(volunteer_achievement.achievement_id),
            "volunteer_id": ObjectId(volunteer_achievement.volunteer_id),
            "received_at": volunteer_achievement.received_at,
        }

        result = await self.collection.insert_one(volunteer_achievement_data)
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})

        return VolunteerAchievement(**inserted_doc)

    async def get_all_volunteer_achievements(self) -> list[VolunteerAchievement]:
        volunteer_achievements_list = await self.collection.find().to_list(length=None)
        return [VolunteerAchievement(**v) for v in volunteer_achievements_list]

    async def get_volunteer_achievement_by_id(
        self, volunteer_achievement_id: str
    ) -> VolunteerAchievement:
        print("Searching for ID: {volunteer_achievement_id}")

        volunteer_achievement = await self.collection.find_one(
            {"_id": ObjectId(volunteer_achievement_id)}
        )

        print("Found document: {volunteer_achievement}")

        if not volunteer_achievement:
            raise HTTPException(status_code=404, detail="Volunteer achievement not found")

        result = VolunteerAchievement(**volunteer_achievement)
        print("Converted result: {result}")
        print("Result type: {type(result)}")

        return result

    async def get_volunteer_achievements_by_achievement_id(
        self, achievement_id: str
    ) -> list[VolunteerAchievement]:
        volunteer_achievements_list = await self.collection.find(
            {"achievement_id": ObjectId(achievement_id)}
        ).to_list(length=None)
        return [VolunteerAchievement(**v) for v in volunteer_achievements_list]

    async def get_volunteer_achievements_by_volunteer(
        self, volunteer_id: str
    ) -> list[VolunteerAchievement]:
        volunteer_achievements_list = await self.collection.find(
            {"volunteer_id": ObjectId(volunteer_id)}
        ).to_list(length=None)
        return [VolunteerAchievement(**v) for v in volunteer_achievements_list]

    async def get_volunteer_received_achievements_by_volunteer(
        self, volunteer_id: str
    ) -> list[VolunteerReceivedAchievementResponse]:
        pipeline = [
            {"$match": {"volunteer_id": ObjectId(volunteer_id)}},
            {
                "$lookup": {
                    "from": "achievements",
                    "localField": "achievement_id",
                    "foreignField": "_id",
                    "as": "achievement",
                }
            },
            {"$unwind": "$achievement"},
            {"$match": {"achievement.is_active": True}},
            {
                "$project": {
                    "_id": {"$toString": "$achievement._id"},
                    "name": "$achievement.name",
                    "description": "$achievement.description",
                    "event_type": "$achievement.event_type",
                    "threshold": "$achievement.threshold",
                    "image_s3_key": "$achievement.image_s3_key",
                    "is_active": "$achievement.is_active",
                    "received_at": "$received_at",
                }
            },
        ]
        return await self.collection.aggregate(pipeline).to_list(length=None)

    async def delete_all_volunteer_achievements_by_achievement(self, achievement_id: str):
        return await self.collection.delete_many({"achievement_id": ObjectId(achievement_id)})

    async def delete_volunteer_achievement(self, volunteer_achievement_id: str) -> None:
        volunteer_achievement_obj_id = parse_object_id(volunteer_achievement_id)

        result = await self.collection.delete_one({"_id": volunteer_achievement_obj_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Volunteer achievement not found")


volunteer_achievement_model = VolunteerAchievementModel.get_instance()
