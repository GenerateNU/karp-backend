from fastapi import HTTPException, status

from app.models.event import event_model
from app.schemas.event import Event
from app.schemas.location import Location


class EventService:
    _instance: "EventService" = None

    def __init__(self, event_model=event_model):
        if EventService._instance is not None:
            raise Exception("This class is a singleton!")
        self.event_model = event_model

    @classmethod
    def get_instance(cls) -> "EventService":
        if EventService._instance is None:
            EventService._instance = cls()
        return EventService._instance

    # ensure that only the org who created the event can modify it
    async def authorize_org(self, event_id: str, org_id: str) -> Event | None:
        event = await self.event_model.get_event_by_id(event_id)
        print(f"Authorizing org {org_id} for event {event_id}")
        print(f"Event org: {event.organization_id }")
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        if event.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this event",
            )

    async def update_event_image(self, event_id: str, s3_key: str, user_id: str) -> str:
        await self.authorize_org(event_id, user_id)
        updated = await self.event_model.update_event_image(event_id, s3_key)
        return updated

    async def get_events_near(self, lat: float, lng: float, distance_km: float) -> list[Event]:
        location = Location(type="Point", coordinates=[lng, lat])
        max_distance_meters = int(distance_km * 1000)
        return await self.event_model.get_events_by_location(max_distance_meters, location)


event_service = EventService.get_instance()
