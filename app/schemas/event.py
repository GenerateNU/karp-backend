from datetime import datetime

from pydantic import BaseModel


class Event(BaseModel):
    name: str
    location: str
    start_date_time: datetime
    end_date_time: datetime
    organization_id: str
    status: str
    max_volunteers: int
    created_at: datetime = datetime.now()

    class Config:
        from_attributes = True


class CreateEventRequest(BaseModel):
    name: str
    location: str
    organization_id: str
    max_volunteers: int
