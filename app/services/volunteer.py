from app.models.volunteer import VolunteerModel
from app.schemas.volunteer import Volunteer
from app.services.volunteer_achievements import VolunteerAchievementsService


class VolunteerService:

    def __init__(self, model=VolunteerModel):
        self.model = model
        self.exp_levels = {
            100: 1,  # 0-100 exp = level 1
            200: 2,  # 101-200 exp = level 2
            500: 3,  # 201-500 exp = level 3
            1000: 4,  # 501-1000 exp = level 4
            1500: 5,  # 1001-2000 exp = level 5
            3000: 6,  # 2001-5000 exp = level 6
            4500: 7,  # 5001-10000 exp = level 7
            6000: 8,
            7500: 9,
            10000: 10,
        }
        self.volunteer_achievements_service = VolunteerAchievementsService()

    async def check_level_up(self, volunteer: Volunteer) -> None:
        current_exp = volunteer["exp"]
        new_level = 1
        for exp_threshold, level in sorted(self.exp_levels.items()):
            if current_exp >= exp_threshold:
                new_level = level
            else:
                break

        if new_level != volunteer["level"]:
            await self.model.update_volunteer(volunteer["id"], {"level": new_level})
            await self.volunteer_achievements_service.add_level_up_achievement(
                volunteer["id"], new_level
            )
