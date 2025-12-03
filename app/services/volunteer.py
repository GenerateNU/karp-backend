import traceback

from app.core.cache_constants import VOLUNTEER_RECEIVED_ACHIEVEMENTS_NAMESPACE
from app.models.volunteer import volunteer_model
from app.schemas.event import Event
from app.schemas.karp_event import KarpEvent
from app.schemas.registration import Registration
from app.schemas.volunteer import UpdateVolunteerRequest, Volunteer
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
        self.growth_factor = 1.75
        self.level_dict = self.create_level_to_xp_dict()

    @classmethod
    def get_instance(cls) -> "VolunteerService":
        if VolunteerService._instance is None:
            VolunteerService._instance = cls()
        return VolunteerService._instance

    async def check_level_up(self, volunteer: Volunteer) -> None:
        current_exp = volunteer.experience
        for level, max_xp in self.level_dict.items():
            if current_exp <= max_xp:
                new_level = level
                break

        if new_level != volunteer.current_level:
            old_level = volunteer.current_level
            update_volunteer_req = UpdateVolunteerRequest(current_level=new_level)
            await self.volunteer_model.update_volunteer(volunteer.id, update_volunteer_req)

            # grant achievements for (old_level + 1) to new_level inclusive
            await self.check_and_grant_achievement(
                volunteer.id, KarpEvent.USER_LEVEL_UP, old_level + 1, new_level
            )

    async def get_level_progress(self, level, cur_xp):
        # TODO: fix later
        if level < 1:
            level = 1
        if level == 1:
            min_xp_cur_level = 0
        else:
            min_xp_cur_level = self.level_dict[level - 1]
        max_xp_cur_level = self.level_dict[level]
        xp_advanced = cur_xp - min_xp_cur_level
        xp_needed_to_advance = max_xp_cur_level - min_xp_cur_level
        progress_percentage = (xp_advanced / xp_needed_to_advance) * 100
        return progress_percentage

    async def check_and_grant_achievement(
        self, volunteer_id: str, event_type: KarpEvent, threshold_min: int, threshold_max: int
    ):
        achievements = await achievement_service.get_achievements_by_threshold(
            event_type, threshold_min, threshold_max
        )
        for achievement in achievements:
            await volunteer_achievements_service._add_achievement_to_volunteer_internal(
                volunteer_id, achievement.id
            )
        if achievements:
            await cache_service.delete(VOLUNTEER_RECEIVED_ACHIEVEMENTS_NAMESPACE, volunteer_id)

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
                print("prev experience:", volunteer.experience)
                new_experience = volunteer.experience + event.coins
                print("new experience:", new_experience)
                print("prev coins:", volunteer.coins)
                new_coins = volunteer.coins + event.coins
                print("new coins", new_coins)
                update_volunteer_req = UpdateVolunteerRequest(
                    experience=new_experience, coins=new_coins
                )
                volunteer = await self.volunteer_model.update_volunteer(
                    volunteer_id, update_volunteer_req
                )
                await self.check_level_up(volunteer)
        except Exception:
            print("Error handling volunteer checkout rewards")
            traceback.print_exc()


volunteer_service = VolunteerService.get_instance()
