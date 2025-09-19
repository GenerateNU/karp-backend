from pydantic import EmailStr

from app.database.mongodb import db
from app.schemas.user import User


class UserModel:
    def __init__(self):
        self.collection = db["users"]

    async def get_by_email(self, email: EmailStr) -> User | None:
        doc = await self.collection.find_one({"email": email})
        return User(**doc) if doc else None

    async def get_by_username(self, username: str) -> User | None:
        doc = await self.collection.find_one({"username": username})
        return User(**doc) if doc else None

    async def get_by_id(self, id: str) -> User | None:
        doc = await self.collection.find_one({"id": id})
        return User(**doc) if doc else None

    async def get_all(self) -> list[User]:
        docs = await self.collection.find().to_list(1000)
        return [User(**doc) for doc in docs]

    async def check_existing_username_and_email(self, username: str, email: EmailStr) -> bool:
        existing_user = await self.collection.find_one(
            {"$or": [{"email": email.lower()}, {"username": username.lower()}]}
        )

        return existing_user is not None

    async def create_user(self, form_data):
        return await self.collection.insert_one(form_data)

    async def delete_all_users(self) -> None:
        await self.collection.delete_many({})

    async def update_password_by_id(self, user_id: str, new_hashed_password: str) -> None:
        await self.collection.update_one(
            {"id": user_id}, {"$set": {"hashed_password": new_hashed_password}}
        )

    async def update_entity_id_by_id(self, user_id: str, entity_id: str) -> None:
        await self.collection.update_one({"id": user_id}, {"$set": {"entity_id": entity_id}})

    async def owns_entity(self, user_id: str, entity_id: str) -> bool:
        user = await user_model.get_by_id(user_id)
        if user and user.entity_id == entity_id:
            return True
        return False


user_model = UserModel()
