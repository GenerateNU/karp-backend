from app.core.cache_constants import VOLUNTEER_RECEIVED_ACHIEVEMENTS_NAMESPACE
from app.models.volunteer import volunteer_model
from app.schemas.karp_event import KarpEvent
from app.schemas.registration import Registration
from app.schemas.volunteer import Volunteer
from app.services.achievement import achievement_service
from app.services.cache import cache_service
from app.services.volunteer_achievements import volunteer_achievements_service


class VolunteerService:
    _instance: "VolunteerService" = None

    def __init__(
        self,
        volunteer_model=volunteer_model,
        volunteer_achievements_service=volunteer_achievements_service,
    ):
        if VolunteerService._instance is not None:
            raise Exception("This class is a singleton!")
        self.volunteer_model = volunteer_model
        self.volunteer_achievements_service = volunteer_achievements_service

        self.base_xp = 100
        self.growth_factor = 1.15

    @classmethod
    def get_instance(cls) -> "VolunteerService":
        if VolunteerService._instance is None:
            VolunteerService._instance = cls()
        return VolunteerService._instance

    async def check_level_up(self, volunteer: Volunteer) -> None:
        current_exp = volunteer["experience"]
        old_level = volunteer["level"]
        new_level = self.compute_level_from_exp(current_exp)

        if new_level != old_level:
            await self.volunteer_model.update_volunteer(volunteer["id"], {"level": new_level})
            await self.check_and_grant_achievement(
                volunteer["id"], KarpEvent.USER_LEVEL_UP, old_level + 1, new_level
            )

    async def check_and_grant_achievement(
        self, volunteer_id: str, event_type: KarpEvent, threshold_min: int, threshold_max: int
    ):
        achievements = await achievement_service.get_achievements_by_threshold(
            event_type, threshold_min, threshold_max
        )
        for achievement in achievements:
            await volunteer_achievements_service.add_achievement_to_volunteer(
                volunteer_id, achievement.id
            )
        await cache_service.delete(VOLUNTEER_RECEIVED_ACHIEVEMENTS_NAMESPACE, volunteer_id)

    def compute_level_from_exp(self, total_exp: int) -> int:
        level = 1
        required_for_next = self.base_xp
        remaining = int(total_exp)
        while remaining >= required_for_next:
            remaining -= required_for_next
            level += 1
            required_for_next = int(required_for_next * self.growth_factor)
            if required_for_next <= 0:
                required_for_next = self.base_xp
        return level

    async def handle_volunteer_checkout_rewards(
        self, registration: Registration, volunteer_id: str, event: dict, volunteer: dict
    ) -> None:
        try:
            if registration.clocked_in and registration.clocked_out:
                duration = registration.clocked_out - registration.clocked_in
                exp_gained = duration.total_seconds() / 36  # 100 exp/hr

                await self.volunteer_model.update_volunteer(
                    volunteer_id, {"$inc": {"experience": int(exp_gained)}}
                )
                await self.volunteer_model.update_volunteer(volunteer_id, {"coins": event["coins"]})
                await self.check_level_up(volunteer)
        except Exception:
            print("Error handling volunteer checkout rewards")
            pass


volunteer_service = VolunteerService.get_instance()
