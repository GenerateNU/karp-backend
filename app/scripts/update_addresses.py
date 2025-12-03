"""
Migration script to update existing organizations, events, and vendors with addresses.

This script will:
1. Find all organizations/events/vendors without valid location data
2. Allow you to provide addresses for them
3. Geocode the addresses and update the location field

Usage:
    python -m app.scripts.update_addresses
"""

import asyncio

from bson import ObjectId

from app.database.mongodb import db
from app.services.geocoding import geocoding_service


async def update_organization_address(org_id: str, address: str) -> bool:
    """Update an organization with a new address."""
    try:
        location = await geocoding_service.location_to_coordinates(address)
        await db["organizations"].update_one(
            {"_id": ObjectId(org_id)}, {"$set": {"location": location.model_dump()}}
        )
        print(f"✓ Updated organization {org_id} with address: {address}")
        return True
    except Exception as e:
        print(f"✗ Failed to update organization {org_id}: {str(e)}")
        return False


async def update_event_address(event_id: str, address: str) -> bool:
    """Update an event with a new address."""
    try:
        location = await geocoding_service.location_to_coordinates(address)
        await db["events"].update_one(
            {"_id": ObjectId(event_id)}, {"$set": {"location": location.model_dump()}}
        )
        print(f"✓ Updated event {event_id} with address: {address}")
        return True
    except Exception as e:
        print(f"✗ Failed to update event {event_id}: {str(e)}")
        return False


async def update_vendor_address(vendor_id: str, address: str) -> bool:
    """Update a vendor with a new address."""
    try:
        location = await geocoding_service.location_to_coordinates(address)
        await db["vendors"].update_one(
            {"_id": ObjectId(vendor_id)}, {"$set": {"location": location.model_dump()}}
        )
        print(f"✓ Updated vendor {vendor_id} with address: {address}")
        return True
    except Exception as e:
        print(f"✗ Failed to update vendor {vendor_id}: {str(e)}")
        return False


async def list_organizations_without_location():
    """List all organizations without valid location data."""
    orgs = (
        await db["organizations"]
        .find(
            {
                "$or": [
                    {"location": {"$exists": False}},
                    {"location": None},
                    {"location.coordinates": {"$exists": False}},
                ]
            }
        )
        .to_list(length=None)
    )

    print(f"\nFound {len(orgs)} organizations without valid location:")
    for org in orgs:
        print(f"  - ID: {org['_id']}, Name: {org.get('name', 'N/A')}")
    return orgs


async def list_events_without_location():
    """List all events without valid location data."""
    events = (
        await db["events"]
        .find(
            {
                "$or": [
                    {"location": {"$exists": False}},
                    {"location": None},
                    {"location.coordinates": {"$exists": False}},
                ]
            }
        )
        .to_list(length=None)
    )

    print(f"\nFound {len(events)} events without valid location:")
    for event in events:
        event_name = event.get("name", "N/A")
        event_address = event.get("address", "N/A")
        print(f"  - ID: {event['_id']}, Name: {event_name}, " f"Address: {event_address}")
    return events


async def list_vendors_without_location():
    """List all vendors without valid location data."""
    vendors = (
        await db["vendors"]
        .find(
            {
                "$or": [
                    {"location": {"$exists": False}},
                    {"location": None},
                    {"location.coordinates": {"$exists": False}},
                ]
            }
        )
        .to_list(length=None)
    )

    print(f"\nFound {len(vendors)} vendors without valid location:")
    for vendor in vendors:
        print(f"  - ID: {vendor['_id']}, Name: {vendor.get('name', 'N/A')}")
    return vendors


async def main():
    """Main migration function."""
    print("=" * 60)
    print("Address Migration Script")
    print("=" * 60)

    # List all entities without locations
    orgs = await list_organizations_without_location()
    events = await list_events_without_location()
    vendors = await list_vendors_without_location()

    total = len(orgs) + len(events) + len(vendors)

    if total == 0:
        print("\n✓ All organizations, events, and vendors have valid locations!")
        return

    print(f"\n{'=' * 60}")
    print(f"Total entities needing addresses: {total}")
    print(f"{'=' * 60}")
    print("\nTo update addresses, use the API endpoints:")
    print("  - PUT /organization/{org_id} with address field")
    print("  - PUT /event/{event_id} with address field")
    print("  - PUT /vendor/{vendor_id} with address field")
    print("\nOr update them manually in MongoDB using the IDs above.")
    print("\nExample MongoDB update command:")
    print("  db.organizations.updateOne(")
    print('    {_id: ObjectId("...")},')
    print('    {$set: {location: {type: "Point", coordinates: [lng, lat]}}}')
    print("  )")


if __name__ == "__main__":
    asyncio.run(main())
