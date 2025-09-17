from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    id: str
    email: EmailStr
    username: str
    hashed_password: str | None = Field(default=None, exclude=True)
    first_name: str | None = None
    last_name: str | None = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    access_token: str
    token_type: str
    user: User

    class Config:
        from_attributes = True
