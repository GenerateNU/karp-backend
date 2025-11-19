from app.core.cache_constants import (
    ACHIEVEMENT_IMAGES_NAMESPACE,
    VOLUNTEER_RECEIVED_ACHIEVEMENTS_NAMESPACE,
)
from app.models.achievement import achievement_model
from app.schemas.achievement import (
    Achievement,
    UpdateAchievementRequest,
    VolunteerReceivedAchievementResponse,
)
from app.schemas.karp_event import KarpEvent
from app.services.cache import cache_service
from app.services.volunteer_achievements import volunteer_achievements_service


class AchievementService:
    _instance: "AchievementService" = None

    def __init__(
        self,
        achievement_model=achievement_model,
    ):
        self.achievement_model = achievement_model

    @classmethod
    def get_instance(cls) -> "AchievementService":
        if AchievementService._instance is None:
            AchievementService._instance = cls()
        return AchievementService._instance

    async def get_achievements_by_threshold(
        self,
        event_type: KarpEvent,
        threshold_min: int | None = None,
        threshold_max: int | None = None,
    ) -> list[Achievement]:
        return await self.achievement_model.get_all_achievements(
            event_type, threshold_min, threshold_max
        )

    async def get_achievements_by_volunteer(
        self,
        volunteer_id: str,
    ) -> list[VolunteerReceivedAchievementResponse]:
        results = (
            await volunteer_achievements_service.get_volunteer_received_achievements_by_volunteer(
                volunteer_id
            )
        )
        return [VolunteerReceivedAchievementResponse(**result) for result in results]

    async def update_achievement(
        self, updated_achievement: UpdateAchievementRequest, achievement_id: str
    ) -> None:
        await self.achievement_model.update_achievement(updated_achievement, achievement_id)
        await self.invalidate_volunteer_received_achievements_caches_by_achievement_id(
            achievement_id
        )

    async def delete_achievement(self, achievement_id: str) -> None:
        # Invalidate caches before deleting volunteer_achievements
        # to avoid losing affected volunteer IDs
        await self.invalidate_volunteer_received_achievements_caches_by_achievement_id(
            achievement_id
        )
        await self.achievement_model.delete_achievement(achievement_id)
        await volunteer_achievements_service._delete_all_by_achievement_id_internal(achievement_id)
        await cache_service.delete(ACHIEVEMENT_IMAGES_NAMESPACE, achievement_id)

    async def invalidate_volunteer_received_achievements_caches_by_achievement_id(
        self, achievement_id: str
    ) -> None:
        volunteer_achievements = (
            await volunteer_achievements_service.get_volunteer_achievements_by_achievement_id(
                achievement_id
            )
        )
        for volunteer_achievement in volunteer_achievements:
            await cache_service.delete(
                VOLUNTEER_RECEIVED_ACHIEVEMENTS_NAMESPACE, volunteer_achievement.volunteer_id
            )


achievement_service = AchievementService.get_instance()
