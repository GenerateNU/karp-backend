from pydantic import EmailStr

from app.database.mongodb import db
from app.schemas.user import UserInDB


class UserModel:
    def __init__(self):
        self.collection = db["users"]

    async def get_by_email(self, email: EmailStr) -> UserInDB:
        return await self.collection.find_one({"email": email})

    async def get_by_username(self, username: str) -> UserInDB:
        return await self.collection.find_one({"username": username})

    async def get_by_id(self, id: str) -> UserInDB:
        return await self.collection.find_one({"id": id})

    async def get_all(self):
        return await self.collection.find().to_list(1000)

    async def check_existing_username_and_email(self, username: str, email: EmailStr) -> bool:
        existing_user = await self.collection.find_one(
            {"$or": [{"email": email.lower()}, {"username": username.lower()}]}
        )

        return existing_user is not None

    async def create_user(self, form_data):
        return await self.collection.insert_one(form_data)


user_model = UserModel()
