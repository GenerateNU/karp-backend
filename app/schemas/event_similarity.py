from datetime import datetime

from pydantic import BaseModel, Field


class SimilarEvent(BaseModel):
    event_id: str
    similarity_score: float = Field(ge=0.0, le=1.0)


class EventSimilarity(BaseModel):
    event_id: str
    similar_events: list[SimilarEvent] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True
