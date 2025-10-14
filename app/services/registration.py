from datetime import datetime

from app.models.registration import registration_model


class RegistrationService:
    def __init__(self):
        pass

    async def update_not_checked_out_volunteers(self, event_id: str) -> None:
        volunteers = await registration_model.get_volunteers_by_event(event_id)
        for volunteer in volunteers:
            if volunteer["clocked_out"] is None:
                volunteer["clocked_out"] = datetime.now()
                await registration_model.update_registration(
                    volunteer["id"], {"clocked_out": volunteer["clocked_out"]}
                )


registration_service = RegistrationService()
