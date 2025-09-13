from datetime import datetime

from pydantic import BaseModel


class Person(BaseModel):
    name: str
    major: str
    fun_fact: str
    favorite_restaurant_in_boston: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    class Config:
        from_attributes = True


class CreatePersonRequest(BaseModel):
    name: str
    major: str
    fun_fact: str
    favorite_restaurant_in_boston: str
