from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.location import Location
from app.services.geocoding import geocoding_service

router = APIRouter()


@router.get("/geocode", response_model=Location)
async def geocode_address(
    address: Annotated[str, Query(description="Address, zipcode, or location to geocode")]
) -> Location:
    """
    Geocode an address, zipcode, or location string to coordinates.
    Returns a Location object with coordinates [longitude, latitude].
    """
    try:
        location = await geocoding_service.location_to_coordinates(address)
        return location
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Geocoding failed: {str(e)}",
        ) from e
