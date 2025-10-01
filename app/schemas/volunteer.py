from enum import Enum

from pydantic import BaseModel

from app.schemas.data_types import Location


class EventType(str, Enum):
    ANIMAL_SHELTER = "Animal Shelter"
    HOMELESS_SHELTER = "Homeless Shelter"
    FOOD_PANTRY = "Food Pantry"
    CLEANUP = "Cleanup"
    TUTORING = "Tutoring"


class Volunteer(BaseModel):
    id: str
    first_name: str
    last_name: str
    age: int
    coins: int
    preferences: list[EventType]  # come back
    is_active: bool = True
    experience: int = 0
    location: Location

    class Config:
        from_attributes = True


class CreateVolunteerRequest(BaseModel):
    first_name: str
    last_name: str
    age: int
    coins: int
    preferences: list[EventType]
    location: Location


class UpdateVolunteerRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    age: int | None = None
    coins: int | None = None
    preferences: list[EventType] | None = None
    is_active: bool | None = None
    location: Location | None = None
