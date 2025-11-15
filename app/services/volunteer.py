from app.models.volunteer import volunteer_model
from app.schemas.event import Event
from app.schemas.registration import Registration
from app.schemas.volunteer import Volunteer
from app.services.volunteer_achievements import volunteer_achievements_service


class VolunteerService:
    _instance: "VolunteerService" = None

    def __init__(
        self,
        volunteer_model=volunteer_model,
        volunteer_achievements_service=volunteer_achievements_service,
    ):
        self.volunteer_model = volunteer_model
        self.volunteer_achievements_service = volunteer_achievements_service

        self.base_xp = 100
        self.growth_factor = 1.75
        self.level_dict = self.create_level_to_xp_dict()

    @classmethod
    def get_instance(cls) -> "VolunteerService":
        if VolunteerService._instance is None:
            VolunteerService._instance = cls()
        return VolunteerService._instance

    async def check_level_up(self, volunteer: Volunteer) -> None:
        current_exp = volunteer.experience
        for level, xp in self.level_dict.items():
            if current_exp <= xp:
                new_level = level
                break

        if new_level != volunteer.current_level:
            await self.volunteer_model.update_volunteer(
                volunteer["id"], {"current_level": new_level}
            )
            await self.volunteer_achievements_service.add_level_up_achievement(
                volunteer["id"], new_level
            )

    def create_level_to_xp_dict(self):
        level_dict = {}
        level = 1
        required_for_next = self.base_xp
        while level <= 100:
            level_dict[level] = required_for_next
            level += 1
            required_for_next = int(required_for_next * self.growth_factor)
        return level_dict

    # computing the level everytime  -- not efficent
    # def compute_level_from_exp(self, total_exp: int) -> int:
    #     level = 1
    #     required_for_next = self.base_xp
    #     remaining = int(total_exp)
    #     while remaining >= required_for_next:
    #         remaining -= required_for_next
    #         level += 1
    #         required_for_next = int(required_for_next * self.growth_factor)
    #         if required_for_next <= 0:
    #             required_for_next = self.base_xp
    #     return level

    # TODO: verify this logic
    async def handle_volunteer_checkout_rewards(
        self, registration: Registration, volunteer_id: str, event: Event, volunteer: Volunteer
    ) -> None:
        try:
            if registration.clocked_in and registration.clocked_out:
                await self.volunteer_model.update_volunteer(
                    volunteer_id, {"$inc": {"experience": event.coins, "coins": event.coins}}
                )
                await self.check_level_up(volunteer)
        except Exception:
            print("Error handling volunteer checkout rewards")
            pass


volunteer_service = VolunteerService.get_instance()
