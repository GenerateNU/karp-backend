from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    username: str
    password: str

    class Config:
        from_attributes = True


class User(UserBase):
    id: str
    username: str

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    id: str
    username: str
    hashed_password: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class UserResponse(BaseModel):
    access_token: str
    token_type: str
    user: User

    class Config:
        from_attributes = True
