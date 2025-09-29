from fastapi import HTTPException, status
from app.schemas.event import Event
from app.schemas.data_types import Location
from app.models.event import event_model
from app.core.config import settings

import requests

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class EventService:
    def __init__(self, model=event_model):
        self.model = model

    # ensure that only the org who created the event can modify it
    async def authorize_org(self, event_id: str, org_id: str) -> Event | None:
        if self.model is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="EventService model dependency not provided",
            )
        event = await self.model.get_event_by_id(event_id)
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

    async def location_to_coordinates(self, address: str) -> list[float]:
        params = {"address": address, "key": settings.GOOGLE_MAPS_KEY}
        response = requests.get(GEOCODE_URL, params=params)
        data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            raise HTTPException(status_code=400, detail=f"Geocoding failed: {data.get('status')}")

        result = data["results"][0]
        location = result["geometry"]["location"]
        return {
            "type": "Point",
            "coordinates": [location["lng"], location["lat"]],
        }
