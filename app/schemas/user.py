from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class UserType(str, Enum):
    VOLUNTEER = "VOLUNTEER"
    VENDOR = "VENDOR"
    ORGANIZATION = "ORGANIZATION"
    ADMIN = "ADMIN"


class User(BaseModel):
    id: str
    email: EmailStr
    username: str
    hashed_password: str = Field(exclude=True)
    first_name: str
    last_name: str
    user_type: UserType
    entity_id: str | None = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    access_token: str
    token_type: str
    user: User

    class Config:
        from_attributes = True


class UserRedirectResponse(BaseModel):
    user_type: UserType
    entity_id: str | None = None

    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    user_type: UserType


class LoginRequest(BaseModel):
    username: str
    password: str


class ResetPasswordRequest(BaseModel):
    current_password: str
    new_password: str
