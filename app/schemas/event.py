from datetime import UTC, datetime
from enum import Enum

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.schemas.location import Location


class EventStatus(str, Enum):
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Event(BaseModel):
    id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    name: str
    address: str
    location: Location | None = None
    start_date_time: datetime
    end_date_time: datetime
    organization_id: str
    status: EventStatus = EventStatus.PUBLISHED
    max_volunteers: int
    coins: int
    description: str | None = None
    keywords: list[str] | None = None
    age_min: int | None = None
    age_max: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str
    image_s3_key: str | None = None
    check_in_qr_code_image: str | None = None
    check_in_qr_token: str | None = None
    check_out_qr_code_image: str | None = None
    check_out_qr_token: str | None = None
    manual_difficulty_coefficient: float = 1.0
    ai_difficulty_coefficient: float = 1.0
    difficulty_coefficient: float = 1.0

    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True,
        populate_by_name=True,
        extra="ignore",
    )

    @field_validator("id", "organization_id", mode="before")
    @classmethod
    def convert_object_id_to_str(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        return value


class CreateEventRequest(BaseModel):
    name: str
    address: str
    start_date_time: datetime
    end_date_time: datetime
    max_volunteers: int
    description: str | None = None
    keywords: list[str] | None = None
    age_min: int | None = None
    age_max: int | None = None
    manual_difficulty_coefficient: float = 1.0
    status: EventStatus = EventStatus.PUBLISHED


class UpdateEventStatusRequest(BaseModel):
    status: EventStatus | None = None
    name: str | None = None
    location: str | None = None
    max_volunteers: int | None = None
    start_date_time: datetime | None = None
    end_date_time: datetime | None = None
    coins: int | None = None
    description: str | None = None
    keywords: list[str] | None = None
    age_min: int | None = None
    age_max: int | None = None
    check_in_qr_code_image: str | None = None
    check_in_qr_token: str | None = None
    check_out_qr_code_image: str | None = None
    check_out_qr_token: str | None = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)
