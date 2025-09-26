from pydantic import BaseModel


class Achievement(BaseModel):
    id: str
    name: str
    description: str
    level: int
    # [How to store fish TBD]

    class Config:
        from_attributes = True


class CreateAchievementRequest(BaseModel):
    name: str
    description: str
    level: int


class UpdateAchievementRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    level: int | None = None
