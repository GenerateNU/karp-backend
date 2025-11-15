from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.location import Location


class EventType(str, Enum):
    ANIMAL_SHELTER = "Animal Shelter"
    HOMELESS_SHELTER = "Homeless Shelter"
    FOOD_PANTRY = "Food Pantry"
    CLEANUP = "Cleanup"
    TUTORING = "Tutoring"


class TrainingDocumentType(str, Enum):  # may use later
    FIRST_AID = "First Aid"
    CPR = "CPR"
    LIFEGUARD = "Life Guard"
    EMT = "EMT"


class TrainingDocument(BaseModel):
    file_type: str  # str for now bc we will have a dropdown for the frontend
    image_s3_key: str


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
    birth_date: datetime
    preferences: list[EventType]  # come back
    training_documents: list[TrainingDocument] = Field(default_factory=list)
    qualifications: list[Qualification]
    preferred_days: list[DayOfWeek]
    is_active: bool = True
    experience: int = 0
    location: Location
    image_s3_key: str | None = None
    current_level: int = 0

    class Config:
        from_attributes = True


class CreateVolunteerRequest(BaseModel):
    first_name: str
    last_name: str
    preferred_name: str | None = None
    birth_date: datetime
    preferences: list[EventType] = []
    qualifications: list[Qualification] = []
    preferred_days: list[DayOfWeek] = []
    location: Location


class UpdateVolunteerRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    coins: int | None = None
    training_document: TrainingDocument | None = None
    preferred_name: str | None = None
    birth_date: datetime | None = None
    preferences: list[EventType] | None = None
    qualifications: list[Qualification] | None = None
    preferred_days: list[DayOfWeek] | None = None
    is_active: bool | None = None
    location: Location | None = None
    phone: str | None = None
    experience: int | None = None
    current_level: int | None = None
