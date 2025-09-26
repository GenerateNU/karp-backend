from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.schemas.achievement import Achievement, CreateAchievementRequest, UpdateAchievementRequest
from app.utils.object_id import parse_object_id


class AchievementModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["achievements"]

    async def create_achievement(
        self, achievement: CreateAchievementRequest, vendor_id: str
    ) -> Achievement:
        achievement_data = achievement.model_dump()

        achievement_data["time_posted"] = datetime.now()
        achievement_data["vendor_id"] = ObjectId(vendor_id)
        achievement_data["status"] = "active"
        achievement_data["price"] = 30  # set to default 30 for now

        result = await self.collection.insert_one(achievement_data)
        inserted_doc = await self.collection.find_one({"_id": result.inserted_id})

        return self.to_achievement(inserted_doc)

    async def get_all_achievements(self) -> list[Achievement]:
        achievements_list = await self.collection.find().to_list(length=None)

        return [self.to_achievement(achievement) for achievement in achievements_list]

    async def get_achievement(self, achievement_id: str) -> Achievement | None:
        achievement_obj_id = parse_object_id(achievement_id)

        achievement = await self.collection.find_one({"_id": achievement_obj_id})

        if achievement is None:
            raise HTTPException(status_code=404, detail="Achievement does not exist!")

        return self.to_achievement(achievement)

    async def deactivate_achievement(self, achievement_id: str) -> None:
        achievement_obj_id = parse_object_id(achievement_id)

        result = await self.collection.update_one(
            {"_id": achievement_obj_id}, {"$set": {"status": "inactive"}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Achievement not found")

    async def activate_achievement(self, achievement_id: str) -> None:
        achievement_obj_id = parse_object_id(achievement_id)

        result = await self.collection.update_one(
            {"_id": achievement_obj_id}, {"$set": {"status": "active"}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Achievement not found")

    async def update_achievement(
        self, updated_achievement: UpdateAchievementRequest, achievement_id: str
    ) -> None:
        achievement_obj_id = parse_object_id(achievement_id)

        # excludes updating fields not provided
        updated_data = updated_achievement.model_dump(exclude_unset=True)

        result = await db["achievements"].update_one(
            {"_id": achievement_obj_id}, {"$set": updated_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Achievement not found")

    # converting id and vendor_id to str to display all achievement fields
    def to_achievement(self, doc) -> Achievement:
        achievement_data = doc.copy()
        achievement_data["id"] = str(achievement_data["_id"])
        achievement_data["vendor_id"] = str(achievement_data["vendor_id"])
        return Achievement(**achievement_data)


achievement_model = AchievementModel()
