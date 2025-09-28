from fastapi import HTTPException

from app.database.mongodb import db
from app.schemas.achievement import Achievement, CreateAchievementRequest, UpdateAchievementRequest
from app.utils.object_id import parse_object_id


class AchievementModel:
    def __init__(self):
        self.collection = db["users"]

    async def create_achievement(self, achievement: CreateAchievementRequest) -> Achievement:
        achievement_data = achievement.model_dump()
        result = await self.collection.insert_one(achievement_data)

        return self.to_achievement(result)

    async def get_all_achievements(self) -> list[Achievement]:
        achievements_list = await self.collection.find().to_list(length=None)

        return [self.to_achievement(achievement) for achievement in achievements_list]

    async def get_achievement(self, achievement_id: str) -> Achievement | None:
        achievement_obj_id = parse_object_id(achievement_id)

        achievement = await self.collection.find_one({"_id": achievement_obj_id})

        if achievement is None:
            raise HTTPException(status_code=404, detail="Achievement does not exist!")

        return self.to_achievement(achievement)

    async def deactivate_achievement(self, achievement_id: str):
        achievement_obj_id = parse_object_id(achievement_id)
        await self.collection.update_one(
            {"_id": achievement_obj_id}, {"$set": {"is_active": False}}
        )

    async def activate_achievement(self, achievement_id: str) -> None:
        achievement_obj_id = parse_object_id(achievement_id)
        result = await self.collection.update_one(
            {"_id": achievement_obj_id}, {"$set": {"is_active": True}}
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
        return Achievement(**achievement_data)


achievement_model = AchievementModel()
