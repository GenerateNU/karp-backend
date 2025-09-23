from enum import Enum

from pydantic import BaseModel


class EventType(str, Enum):
    ANIMAL_SHELTER = "Animal Shelter"
    HOMELESS_SHELTER = "Homeless Shelter"
    FOOD_PANTRY = "Food Pantry"
    CLEANUP = "Cleanup"
    TUTORING = "Tutoring"


class Volunteer(BaseModel):
    id: str
    firstName: str
    lastName: str
    trainings: list[str]  ## come back to this
    age: int
    coins: int
    preferences: list[EventType]  # come back
    isActive: bool = True

    class Config:
        from_attributes = True


class CreateVolunteerRequest(BaseModel):
    firstName: str
    lastName: str
    trainings: list[str]
    age: int
    coins: int
    preferences: list[EventType]


class UpdateVolunteerRequest(BaseModel):
    firstName: str | None = None
    lastName: str | None = None
    trainings: list[str] | None = None
    age: int | None = None
    coins: int | None = None
    preferences: list[EventType] | None = None
    isActive: bool | None = None
