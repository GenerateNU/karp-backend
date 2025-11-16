from fastapi import HTTPException, status
from httpx import AsyncClient

from app.core.config import settings
from app.schemas.location import Location


class GeocodingService:
    _instance: "GeocodingService" = None

    def __init__(self):
        if GeocodingService._instance is not None:
            raise Exception("This class is a singleton!")
        self.geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"

    @classmethod
    def get_instance(cls) -> "GeocodingService":
        if GeocodingService._instance is None:
            GeocodingService._instance = cls()
        return GeocodingService._instance

    async def location_to_coordinates(self, address: str) -> Location:
        params = {"address": address, "key": settings.GOOGLE_MAPS_KEY}
        async with AsyncClient(timeout=10) as client:
            r = await client.get(self.geocode_url, params=params)
        if r.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail="Geocoding upstream error"
            )
        data = r.json()
        if data.get("status") != "OK" or not data.get("results"):
            raise HTTPException(status_code=400, detail=f"Geocoding failed: {data.get('status')}")
        loc = data["results"][0]["geometry"]["location"]

        return Location(type="Point", coordinates=[loc["lng"], loc["lat"]])


geocoding_service = GeocodingService.get_instance()
