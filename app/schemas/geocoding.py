from pydantic import BaseModel

from app.schemas.address import Address
from app.schemas.location import Location


class GeocodingResponse(BaseModel):
    """Response from geocoding service with both location and structured address"""

    location: Location
    address: Address


class GeocodingResult(BaseModel):
    """Internal result from geocoding service"""

    location: Location
    address: Address
