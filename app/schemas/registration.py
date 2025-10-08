from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class RegistrationStatus(str, Enum):
    UPCOMING = "upcoming"
    COMPLETED = "completed"
    INCOMPLETED = "incompleted"
    UNREGISTERED = "unregistered"


class Registration(BaseModel):
    id: str
    event_id: str
    volunteer_id: str
    registered_at: datetime
    registration_status: RegistrationStatus
    clocked_in: datetime | None
    clocked_out: datetime | None

    class Config:
        from_attributes = True


class CreateRegistrationRequest(BaseModel):
    event_id: str
