from __future__ import annotations
from typing import Any
from fastapi import HTTPException, status
from app.schemas.data_types import Location
from app.core.config import settings
from httpx import AsyncClient

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class EventService:
    def __init__(self):
        pass

    def authorize_org(self, event: dict[str, Any], org_id: str) -> None:
        """Helper to check if organization can modify event"""
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        if event.get("organization_id") != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this event",
            )

    async def location_to_coordinates(self, address: str) -> Location:
        """Helper to convert address to coordinates via Google Maps API"""
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
        return Location(type="Point", coordinates=[loc["lng"], loc["lat"]])

    def calculate_exp_reward(self, start_time: Any, end_time: Any) -> float:
        """Helper to calculate EXP reward based on event duration"""
        duration = end_time - start_time
        return duration.total_seconds() / 36  # 3600 seconds in an hour * 100 exp per hour
