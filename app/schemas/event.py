from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class Status(Enum):
    PUBLISHED = "published"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DRAFT = "draft"
    DELETED = "deleted"

class Event(BaseModel):
    name: str
    location: str
    start_date_time: datetime
    end_date_time: datetime
    organization_id: str
    status: Status
    max_volunteers: int
    created_at: datetime = datetime.now()

    class Config:
        from_attributes = True
        use_enum_values = True

class CreateEventRequest(BaseModel):
    name: str
    location: str
    start_date_time: datetime
    end_date_time: datetime
    organization_id: str
    max_volunteers: int

class UpdateEventStatusRequestDTO(BaseModel):
    status: Status
    name: str
    location: str
    max_volunteers: int
    start_date_time: datetime
    end_date_time: datetime

    class Config:
        use_enum_values = True
        from_attributes = True
