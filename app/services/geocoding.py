from fastapi import HTTPException, status
from httpx import AsyncClient

from app.core.config import settings
from app.schemas.geocoding import GeocodingResult
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

    async def geocode_address(self, address: str) -> GeocodingResult:
        """
        Geocode an address and return both location coordinates and structured address.
        """
        result = await self._geocode_internal(address)
        return result

    async def location_to_coordinates(self, address: str) -> Location:
        """
        Geocode an address and return only the location coordinates (for backward compatibility).
        """
        result = await self._geocode_internal(address)
        return result.location

    async def _geocode_internal(self, address: str) -> GeocodingResult:
        # Validate input
        if not address or not address.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Address cannot be empty. "
                    "Please provide a zipcode, address, or location name."
                ),
            )

        # Check if API key is configured
        if not settings.GOOGLE_MAPS_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Geocoding service is not configured. Please contact support.",
            )

        params = {"address": address.strip(), "key": settings.GOOGLE_MAPS_KEY}

        try:
            async with AsyncClient(timeout=10) as client:
                r = await client.get(self.geocode_url, params=params)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to geocoding service: {str(e)}",
            ) from e

        if r.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Geocoding service returned error status {r.status_code}",
            )

        try:
            data = r.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Invalid response from geocoding service: {str(e)}",
            ) from e

        status_code = data.get("status")

        # Handle different Google Maps API status codes
        if status_code == "ZERO_RESULTS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Could not find location for '{address}'. "
                    "Please try a different address or zipcode."
                ),
            )
        elif status_code == "OVER_QUERY_LIMIT":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Geocoding service quota exceeded. Please try again later.",
            )
        elif status_code == "REQUEST_DENIED":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Geocoding service access denied. Please contact support.",
            )
        elif status_code == "INVALID_REQUEST":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid address format: '{address}'. "
                    "Please provide a valid address or zipcode."
                ),
            )
        elif status_code != "OK" or not data.get("results"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geocoding failed with status: {status_code}",
            )

        try:
            result = data["results"][0]
            loc = result["geometry"]["location"]
            formatted_address = result.get("formatted_address")

            # Extract structured address components
            address_components = result.get("address_components", [])
            address_data = {}

            for component in address_components:
                types = component.get("types", [])
                long_name = component.get("long_name", "")

                if "street_number" in types:
                    address_data["street_number"] = long_name
                elif "route" in types:
                    address_data["street_name"] = long_name
                elif "locality" in types or "sublocality" in types:
                    address_data["city"] = long_name
                elif "administrative_area_level_1" in types:
                    address_data["state"] = long_name
                elif "postal_code" in types:
                    address_data["zipcode"] = long_name
                elif "country" in types:
                    address_data["country"] = long_name

            address_data["formatted_address"] = formatted_address
            # Store address in the result for later use
            # For now, we'll just return the location as before
            # but we can enhance this to return both if needed

            return Location(type="Point", coordinates=[loc["lng"], loc["lat"]])
        except (KeyError, IndexError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unexpected response format from geocoding service: {str(e)}",
            ) from e


geocoding_service = GeocodingService.get_instance()
