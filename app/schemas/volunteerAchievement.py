from datetime import datetime

from pydantic import BaseModel


class VolunteerAchievement(BaseModel):
    id: str
    achievement_id: str
    volunteer_id: str
    received_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class CreateVolunteerAchievementRequest(BaseModel):
    achievement_id: str
    volunteer_id: str


# class UpdateVolunteerAchievementRequest(BaseModel):
#     volunteerAchievement_status: OrderStatus
