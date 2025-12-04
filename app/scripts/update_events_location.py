"""
Python script to update all events without valid locations
with the location: 360 Huntington Ave, Boston, MA 02115

Usage:
    python -m app.scripts.update_events_location
"""

import asyncio

from app.database.mongodb import db
from app.services.geocoding import geocoding_service


async def update_events_without_location():
    """Update all events without valid locations with a default address."""
    target_address = "360 Huntington Ave, Boston, MA 02115"

    try:
        # Geocode the target address
        location = await geocoding_service.location_to_coordinates(target_address)
        print(f"Geocoded address '{target_address}' to coordinates: {location.coordinates}")

        # Find events without valid location
        query = {
            "$or": [
                {"location": {"$exists": False}},
                {"location": None},
                {"location.coordinates": {"$exists": False}},
                {"location.coordinates": None},
            ]
        }

        # Count how many will be updated
        count = await db["events"].count_documents(query)
        print(f"\nFound {count} events without valid locations")

        if count == 0:
            print("No events need updating!")
            return

        # Update all matching events
        result = await db["events"].update_many(
            query, {"$set": {"location": location.model_dump(), "address": target_address}}
        )

        print(f"\n✓ Updated {result.modified_count} events")
        print(f"  Address: {target_address}")
        print(f"  Location: {location.model_dump()}")

    except Exception as e:
        print(f"✗ Error updating events: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(update_events_without_location())
