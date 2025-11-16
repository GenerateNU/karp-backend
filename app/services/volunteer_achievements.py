from app.core.cache_constants import VOLUNTEER_RECEIVED_ACHIEVEMENTS_NAMESPACE
from app.models.achievement import achievement_model
from app.models.volunteer_achievement import (
    CreateVolunteerAchievementRequest,
    VolunteerAchievement,
    volunteer_achievement_model,
)
from app.schemas.achievement import VolunteerReceivedAchievementResponse
from app.services.cache import cache_service


class VolunteerAchievementsService:
    _instance: "VolunteerAchievementsService" = None

    def __init__(
        self,
        volunteer_achievement_model=volunteer_achievement_model,
        achievement_model=achievement_model,
    ):
        if VolunteerAchievementsService._instance is not None:
            raise Exception("This class is a singleton!")
        self.volunteer_achievement_model = volunteer_achievement_model
        self.achievement_model = achievement_model

    @classmethod
    def get_instance(cls) -> "VolunteerAchievementsService":
        if VolunteerAchievementsService._instance is None:
            VolunteerAchievementsService._instance = cls()
        return VolunteerAchievementsService._instance

    async def get_volunteer_achievements_by_volunteer(
        self, volunteer_id: str
    ) -> list[VolunteerAchievement]:
        return await self.volunteer_achievement_model.get_volunteer_achievements_by_volunteer(
            volunteer_id
        )

    async def get_volunteer_achievements_by_achievement_id(
        self, achievement_id: str
    ) -> list[VolunteerAchievement]:
        return await self.volunteer_achievement_model.get_volunteer_achievements_by_achievement_id(
            achievement_id
        )

    # Internal method to delete all volunteer achievements by achievement ID, no cache invalidation
    async def _delete_all_by_achievement_id_internal(self, achievement_id: str):
        return (
            await self.volunteer_achievement_model.delete_all_volunteer_achievements_by_achievement(
                achievement_id
            )
        )

    # Internal method to add an achievement to a volunteer, no cache invalidation
    async def _add_achievement_to_volunteer_internal(self, volunteer_id: str, achievement_id: str):
        existing_achievements = (
            await self.volunteer_achievement_model.get_volunteer_achievements_by_volunteer(
                volunteer_id
            )
        )
        if achievement_id in [achievement.achievement_id for achievement in existing_achievements]:
            return
        return await self.volunteer_achievement_model.create_volunteer_achievement(
            CreateVolunteerAchievementRequest(
                volunteer_id=volunteer_id, achievement_id=achievement_id
            )
        )

    async def get_volunteer_received_achievements_by_volunteer(
        self, volunteer_id: str
    ) -> list[VolunteerReceivedAchievementResponse]:
        return (
            await self.volunteer_achievement_model.get_volunteer_received_achievements_by_volunteer(
                volunteer_id
            )
        )

    async def create_volunteer_achievement(
        self, volunteer_achievement: CreateVolunteerAchievementRequest
    ) -> VolunteerAchievement:
        await cache_service.delete(
            VOLUNTEER_RECEIVED_ACHIEVEMENTS_NAMESPACE, volunteer_achievement.volunteer_id
        )
        return await self.volunteer_achievement_model.create_volunteer_achievement(
            volunteer_achievement
        )

    async def delete_volunteer_achievement(self, volunteer_achievement_id: str) -> None:
        volunteer_id = await self.volunteer_achievement_model.get_volunteer_achievement_by_id(
            volunteer_achievement_id
        )
        await cache_service.delete(VOLUNTEER_RECEIVED_ACHIEVEMENTS_NAMESPACE, volunteer_id)

        return await self.volunteer_achievement_model.delete_volunteer_achievement(
            volunteer_achievement_id
        )


volunteer_achievements_service = VolunteerAchievementsService.get_instance()
