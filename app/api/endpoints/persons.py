from typing import Annotated

from app.models.person import person_model
from app.schemas.person import CreatePersonRequest, Person
from fastapi import APIRouter, Body

router = APIRouter()


@router.post("/new", response_model=Person)
async def create_person(person: Annotated[CreatePersonRequest, Body(...)]) -> Person:
    return await person_model.create_person(person)


@router.get("/all", response_model=list[Person])
async def get_persons() -> list[Person]:
    return await person_model.get_all_persons()


@router.delete("/clear", response_model=None)
async def clear_persons() -> None:
    return await person_model.delete_all_persons()
