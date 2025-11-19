from datetime import datetime
from typing import TYPE_CHECKING

from bson import ObjectId

from app.database.mongodb import db
from app.schemas.event_similarity import EventSimilarity

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


class EventSimilarityModel:
    _instance: "EventSimilarityModel | None" = None

    def __init__(self) -> None:
        self.collection: AsyncIOMotorCollection = db["event_similarities"]

    @classmethod
    def get_instance(cls) -> "EventSimilarityModel":
        if EventSimilarityModel._instance is None:
            EventSimilarityModel._instance = cls()
        return EventSimilarityModel._instance

    async def create_indexes(self) -> None:
        try:
            await self.collection.create_index("event_id", unique=True)
        except Exception:
            pass

    async def upsert_similarities(
        self, event_id: str, similar_events: list[dict[str, float | str]]
    ) -> EventSimilarity:
        data = {
            "event_id": ObjectId(event_id),
            "similar_events": [
                {
                    "event_id": ObjectId(str(se["event_id"])),
                    "similarity_score": float(se["similarity_score"]),
                }
                for se in similar_events
            ],
            "last_updated": datetime.now(),
        }

        await self.collection.update_one(
            {"event_id": ObjectId(event_id)}, {"$set": data}, upsert=True
        )

        doc = await self.collection.find_one({"event_id": ObjectId(event_id)})
        if doc is None:
            raise ValueError(f"Failed to upsert similarities for event {event_id}")

        return EventSimilarity(**doc)

    async def get_similar_events(self, event_id: str) -> EventSimilarity | None:
        doc = await self.collection.find_one({"event_id": ObjectId(event_id)})
        return EventSimilarity(**doc) if doc else None

    async def get_all_similarities(self) -> list[EventSimilarity]:
        docs = await self.collection.find().to_list(length=None)
        return [EventSimilarity(**doc) for doc in docs]

    async def delete_similarity(self, event_id: str) -> None:
        await self.collection.delete_one({"event_id": ObjectId(event_id)})


event_similarity_model = EventSimilarityModel.get_instance()
