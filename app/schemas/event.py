from datetime import UTC, datetime

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.schemas.location import Location
from app.schemas.status import Status


class Event(BaseModel):
    id: str = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    name: str
    address: str
    location: Location | None = None
    start_date_time: datetime
    end_date_time: datetime
    organization_id: str
    status: Status
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
    coins: int
    description: str | None = None
    keywords: list[str] | None = None
    age_min: int | None = None
    age_max: int | None = None


class UpdateEventStatusRequest(BaseModel):
    status: Status | None = None
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
