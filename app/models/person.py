from motor.motor_asyncio import AsyncIOMotorCollection  # noqa: TCH002

from app.database.mongodb import db
from app.schemas.person import CreatePersonRequest, Person


class PersonModel:
    def __init__(self):
        self.collection: AsyncIOMotorCollection = db["persons"]

    async def create_person(self, person: CreatePersonRequest) -> Person:
        person_data = person.model_dump()

        await self.collection.insert_one(person_data)

        return Person(**person_data)

    async def get_all_persons(self) -> list[Person]:
        persons_list = await self.collection.find().to_list(length=None)

        return [Person(**person) for person in persons_list]

    async def delete_all_persons(self) -> None:
        await self.collection.delete_many({})


person_model = PersonModel()
