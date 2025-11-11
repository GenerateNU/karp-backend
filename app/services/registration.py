from datetime import datetime

from app.models.registration import registration_model


class RegistrationService:
    _instance: "RegistrationService" = None

    def __init__(self, registration_model=registration_model):
        if RegistrationService._instance is not None:
            raise Exception("This class is a singleton!")
        self.registration_model = registration_model

    @classmethod
    def get_instance(cls) -> "RegistrationService":
        if RegistrationService._instance is None:
            RegistrationService._instance = cls()
        return RegistrationService._instance

    async def update_not_checked_out_volunteers(self, event_id: str) -> None:
        volunteers = await self.registration_model.get_volunteers_by_event(event_id)
        for volunteer in volunteers:
            if volunteer["clocked_out"] is None:
                volunteer["clocked_out"] = datetime.now()
                await self.registration_model.update_registration(
                    volunteer["id"], {"clocked_out": volunteer["clocked_out"]}
                )


registration_service = RegistrationService.get_instance()
