from fastapi import HTTPException, status
from app.schemas.event import Event
from app.schemas.data_types import Location
from app.core.config import settings
from app.models.event import event_model
from httpx import AsyncClient

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class EventService:
    def __init__(self):
        self.event_model = event_model
        pass

    # ensure that only the org who created the event can modify it
    async def authorize_org(self, event_id: str, org_id: str) -> Event | None:
        event = await event_model.get_event_by_id(event_id)
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

    async def location_to_coordinates(self, address: str) -> Location:
        params = {"address": address, "key": settings.GOOGLE_MAPS_KEY}
        async with AsyncClient(timeout=10) as client:
            r = await client.get(GEOCODE_URL, params=params)
        if r.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail="Geocoding upstream error"
            )
        data = r.json()
        if data.get("status") != "OK" or not data.get("results"):
            raise HTTPException(status_code=400, detail=f"Geocoding failed: {data.get('status')}")
        loc = data["results"][0]["geometry"]["location"]
        # Return your schema type
        return Location(type="Point", coordinates=[loc["lng"], loc["lat"]])
