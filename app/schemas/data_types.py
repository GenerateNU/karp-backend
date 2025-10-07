from enum import Enum

from pydantic import BaseModel


class Status(str, Enum):
    PUBLISHED = "PUBLISHED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DRAFT = "DRAFT"
    DELETED = "DELETED"


class Location(BaseModel):
    type: str
    coordinates: list[float]


class EventType(str, Enum):
    ANIMAL_SHELTER = "Animal Shelter"
    HOMELESS_SHELTER = "Homeless Shelter"
    FOOD_PANTRY = "Food Pantry"
    CLEANUP = "Cleanup"
    TUTORING = "Tutoring"
