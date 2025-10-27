from app.models.volunteer import VolunteerModel
from app.schemas.volunteer import Volunteer
from app.schemas.registration import Registration
from app.services.volunteer_achievements import VolunteerAchievementsService


class VolunteerService:

    def __init__(self, model=VolunteerModel):
        self.model = model

        self.base_xp = 100
        self.growth_factor = 1.15
        self.volunteer_achievements_service = VolunteerAchievementsService()

    async def check_level_up(self, volunteer: Volunteer) -> None:
        current_exp = volunteer["experience"]
        new_level = self.compute_level_from_exp(current_exp)

        if new_level != volunteer["level"]:
            await self.model.update_volunteer(volunteer["id"], {"level": new_level})
            await self.volunteer_achievements_service.add_level_up_achievement(
                volunteer["id"], new_level
            )

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

                await self.model.update_volunteer(
                    volunteer_id, {"$inc": {"experience": int(exp_gained)}}
                )
                await self.model.update_volunteer(volunteer_id, {"coins": event["coins"]})
                await self.check_level_up(volunteer)
        except Exception:
            print("Error handling volunteer checkout rewards")
            pass
