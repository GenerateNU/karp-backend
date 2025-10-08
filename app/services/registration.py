from datetime import datetime
from app.models.registration import registration_model


class RegistrationService:
    def __init__(self, model=None):
        self.model = registration_model

    async def update_not_checked_out_volunteers(self, event_id: str) -> None:
        volunteers = await self.model.get_volunteers_by_event(event_id)
        for volunteer in volunteers:
            if volunteer["clocked_out"] is None:
                volunteer["clocked_out"] = datetime.now()
                await self.model.update_registration(
                    volunteer["id"], {"clocked_out": volunteer["clocked_out"]}
                )
