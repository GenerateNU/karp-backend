# app/services/context.py
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.registration import RegistrationService
    from app.services.volunteer import VolunteerService
    from app.services.event import EventService
    from app.services.volunteer_achievements import VolunteerAchievementsService


# Use string annotations to avoid import-time cycles.
@dataclass
class ServiceContext:
    # Add the services we actually need. Examples:
    registration: "RegistrationService" | None = None
    volunteer: "VolunteerService" | None = None
    event: "EventService" | None = None
    volunteer_achievements: "VolunteerAchievementsService" | None = None
    # Add more as needed: notifier, geocode, analytics, etc.

    # Optional: small helpers to assert presence for clearer errors.
    def need_registration(self) -> "RegistrationService":
        assert self.registration is not None, "registration service not provided"
        return self.registration

    def need_volunteer(self) -> "VolunteerService":
        assert self.volunteer is not None, "volunteer service not provided"
        return self.volunteer

    def need_event(self) -> "EventService":
        assert self.event is not None, "event service not provided"
        return self.event

    def need_volunteer_achievements(self) -> "VolunteerAchievementsService":
        assert (
            self.volunteer_achievements is not None
        ), "volunteer achievements service not provided"
        return self.volunteer_achievements
