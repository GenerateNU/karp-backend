from datetime import date
from enum import Enum

from pydantic import BaseModel

from app.schemas.data_types import Location


class EventType(str, Enum):
    ANIMAL_SHELTER = "Animal Shelter"
    HOMELESS_SHELTER = "Homeless Shelter"
    FOOD_PANTRY = "Food Pantry"
    CLEANUP = "Cleanup"
    TUTORING = "Tutoring"


class Qualification(str, Enum):
    CPR_CERTIFIED = "CPR Certified"
    ELDER_CARE = "Elder Care"
    FOOD_DELIVERY = "Food Delivery/Distribution"
    MULTILINGUAL = "Multilingual"
    TUTORING = "Tutoring"
    RESEARCH = "Research"
    WRITING = "Writing/Journalism"


class DayOfWeek(str, Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


class Volunteer(BaseModel):
    id: str
    first_name: str
    last_name: str
    coins: int = 0
    preferred_name: str | None = None
    birth_date: date
    preferences: list[EventType]  # come back
    qualifications: list[Qualification]
    preferred_days: list[DayOfWeek]
    is_active: bool = True
    experience: int = 0
    location: Location

    class Config:
        from_attributes = True


class CreateVolunteerRequest(BaseModel):
    first_name: str
    last_name: str
    preferred_name: str | None = None
    birth_date: date
    preferences: list[EventType] = []
    qualifications: list[Qualification] = []
    preferred_days: list[DayOfWeek] = []
    location: Location


class UpdateVolunteerRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    coins: int | None = None
    preferred_name: str | None = None
    birth_date: date | None = None
    preferences: list[EventType] | None = None
    qualifications: list[Qualification] | None = None
    preferred_days: list[DayOfWeek] | None = None
    is_active: bool | None = None
    location: Location | None = None
