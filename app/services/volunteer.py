from app.models.volunteer import VolunteerModel
from app.schemas.volunteer import Volunteer
from app.services.volunteer_achievements import VolunteerAchievementsService


class VolunteerService:

    def __init__(self, model=VolunteerModel):
        self.model = model

        self.base_xp = 100
        self.growth_factor = 1.15
        self.volunteer_achievements_service = VolunteerAchievementsService()

    async def check_level_up(self, volunteer: Volunteer) -> None:
        current_exp = volunteer["exp"]
        new_level = self._compute_level_from_exp(current_exp)

        if new_level != volunteer["level"]:
            await self.model.update_volunteer(volunteer["id"], {"level": new_level})
            await self.volunteer_achievements_service.add_level_up_achievement(
                volunteer["id"], new_level
            )

    def _compute_level_from_exp(self, total_exp: int) -> int:
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
