from app.models.volunteer_achievement import volunteer_achievement_model, CreateVolunteerAchievementRequest
from app.models.achievement import achievement_model
from app.schemas.achievement import Achievement


class VolunteerAchievementsService:
    def __init__(self, model=volunteer_achievement_model):
        self.model = model
        self.achievements_model = achievement_model

    async def add_achievement_to_volunteer(self, volunteer_id: str, achievement_id: str):
        volunteer_achievement_request = CreateVolunteerAchievementRequest(
            volunteer_id=volunteer_id, achievement_id=achievement_id
        )
        return await self.model.create_volunteer_achievement(volunteer_achievement_request)

    async def get_achievements_by_level(self, level: int) -> Achievement:
        return await self.achievement_model.get_achievements_by_level(level)

    async def add_level_up_achievement(self, volunteer_id: str, level: int) -> None:
        achievements = await self.get_achievements_by_level(level)
        for achievement in achievements:
            await self.add_achievement_to_volunteer(volunteer_id, achievement["id"])