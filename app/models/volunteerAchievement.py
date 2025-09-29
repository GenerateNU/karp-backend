from datetime import datetime
from typing import TYPE_CHECKING

from bson import ObjectId
from fastapi import HTTPException

from app.database.mongodb import db
from app.schemas.volunteerAchievement import CreateVolunteerAchievementRequest, VolunteerAchievement
from app.utils.object_id import parse_object_id

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


class VolunteerAchievementModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["volunteerAchievements"]

    async def create_volunteer_achievement(
        self, volunteerAchievement: CreateVolunteerAchievementRequest
    ) -> VolunteerAchievement:
        volunteer_achievement_data = {
            "achievement_id": ObjectId(volunteerAchievement.achievement_id),
            "volunteer_id": ObjectId(volunteerAchievement.volunteer_id),
            "received_at": datetime.now(),
        }

        result = await self.collection.insert_one(volunteer_achievement_data)
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})

        return self._to_volunteer_achievement(inserted_doc)

    async def get_all_volunteer_achievements(self) -> list[VolunteerAchievement]:
        volunteer_achievements_list = await self.collection.find().to_list(length=None)
        return [
            self._to_volunteer_achievement(volunteer_achievement)
            for volunteer_achievement in volunteer_achievements_list
        ]

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

        result = self._to_volunteer_achievement(volunteer_achievement)
        print("Converted result: {result}")
        print("Result type: {type(result)}")

        return result

    async def get_volunteer_achievements_by_achievement(
        self, achievement_id: str
    ) -> list[VolunteerAchievement]:
        volunteer_achievements_list = await self.collection.find(
            {"achievement_id": ObjectId(achievement_id)}
        ).to_list(length=None)
        return [
            self._to_volunteer_achievement(volunteer_achievement)
            for volunteer_achievement in volunteer_achievements_list
        ]

    async def get_volunteer_achievements_by_volunteer(
        self, volunteer_id: str
    ) -> list[VolunteerAchievement]:
        volunteer_achievements_list = await self.collection.find(
            {"volunteer_id": ObjectId(volunteer_id)}
        ).to_list(length=None)
        return [
            self._to_volunteer_achievement(volunteerAchievement)
            for volunteerAchievement in volunteer_achievements_list
        ]

    async def delete_volunteer_achievement(self, volunteer_achievement_id: str) -> None:
        volunteer_achievement_obj_id = parse_object_id(volunteer_achievement_id)

        result = await self.collection.delete_one({"_id": volunteer_achievement_obj_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Volunteer achievement not found")

    def _to_volunteer_achievement(self, doc) -> VolunteerAchievement:
        volunteer_achievement_data = doc.copy()
        volunteer_achievement_data["id"] = str(volunteer_achievement_data["_id"])
        volunteer_achievement_data["achievement_id"] = str(
            volunteer_achievement_data["achievement_id"]
        )
        volunteer_achievement_data["volunteer_id"] = str(volunteer_achievement_data["volunteer_id"])

        volunteer_achievement_data.pop("_id")

        return VolunteerAchievement(**volunteer_achievement_data)


volunteer_achievement_model = VolunteerAchievementModel()
