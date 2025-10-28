from pydantic import BaseModel


class Location(BaseModel):
    type: str
    coordinates: list[float]
