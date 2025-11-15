from fastapi import HTTPException

from app.database.mongodb import db
from app.schemas.achievement import Achievement, CreateAchievementRequest, UpdateAchievementRequest
from app.schemas.karp_event import KarpEvent
from app.utils.object_id import parse_object_id


class AchievementModel:
    _instance: "AchievementModel" = None

    def __init__(self):
        self.collection = db["achievements"]

    @classmethod
    def get_instance(cls) -> "AchievementModel":
        if AchievementModel._instance is None:
            AchievementModel._instance = cls()
        return AchievementModel._instance

    async def create_achievement(self, achievement: CreateAchievementRequest) -> Achievement:
        achievement_data = achievement.model_dump()
        result = await self.collection.insert_one(achievement_data)

        achievement_data["_id"] = result.inserted_id

        return Achievement(**achievement_data)

    async def get_all_achievements(
        self,
        event_type: KarpEvent | None = None,
        threshold_min: int | None = None,
        threshold_max: int | None = None,
    ) -> list[Achievement]:
        filters = {"is_active": True}
        if event_type is not None:
            filters["event_type"] = event_type
        threshold_filter = {}
        if threshold_min is not None:
            threshold_filter["$gte"] = threshold_min
        if threshold_max is not None:
            threshold_filter["$lte"] = threshold_max
        if threshold_filter:
            filters["threshold"] = threshold_filter
        achievements_list = await self.collection.find(filters).to_list(length=None)

        return [Achievement(**achievement) for achievement in achievements_list]

    async def get_achievement(self, achievement_id: str) -> Achievement | None:
        achievement_obj_id = parse_object_id(achievement_id)

        achievement = await self.collection.find_one({"_id": achievement_obj_id})

        if achievement is None:
            raise HTTPException(status_code=404, detail="Achievement does not exist")

        return Achievement(**achievement)

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

        updated_data = updated_achievement.model_dump(exclude_unset=True)

        result = await self.collection.update_one(
            {"_id": achievement_obj_id}, {"$set": updated_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Achievement not found")

    async def delete_achievement(self, achievement_id: str) -> None:
        achievement_obj_id = parse_object_id(achievement_id)

        result = await self.collection.delete_one({"_id": achievement_obj_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Achievement not found")

    async def update_achievement_image(self, achievement_id: str, s3_key: str) -> str:
        achievement_obj_id = parse_object_id(achievement_id)
        result = await self.collection.update_one(
            {"_id": achievement_obj_id}, {"$set": {"image_s3_key": s3_key}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Achievement not found")
        return s3_key


achievement_model = AchievementModel.get_instance()
