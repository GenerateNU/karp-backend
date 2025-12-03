import logging

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
        self.logger = logging.getLogger(__name__)

    @classmethod
    def get_instance(cls) -> "GeocodingService":
        if GeocodingService._instance is None:
            GeocodingService._instance = cls()
        return GeocodingService._instance

    async def location_to_coordinates(self, address: str) -> Location:
        params = {"address": address, "key": settings.GOOGLE_MAPS_KEY}
        async with AsyncClient(timeout=20) as client:
            r = await client.get(self.geocode_url, params=params)
        if r.status_code != 200:
            # Log upstream response for diagnosis (does not include secrets)
            try:
                self.logger.error(
                    "Geocoding upstream HTTP error %s for address '%s': %s",
                    r.status_code,
                    address,
                    r.text,
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail="Geocoding upstream error"
            )
        data = r.json()
        if data.get("status") != "OK" or not data.get("results"):
            # Include Google's error_message when present to distinguish configuration issues
            error_message = data.get("error_message")
            self.logger.warning(
                "Geocoding failed for address '%s' with status '%s' and message '%s'",
                address,
                data.get("status"),
                error_message,
            )
            detail = f"Geocoding failed: {data.get('status')}" + (
                f" - {error_message}" if error_message else ""
            )
            raise HTTPException(status_code=400, detail=detail)
        loc = data["results"][0]["geometry"]["location"]

        return Location(type="Point", coordinates=[loc["lng"], loc["lat"]])


geocoding_service = GeocodingService.get_instance()
