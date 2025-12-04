"""
Script to backfill item locations from their vendor locations.
Run this to populate location for existing items that don't have one.
"""

import asyncio

from app.database.mongodb import db


async def backfill_item_locations():
    """Backfill location for items that don't have one, using their vendor's location."""
    items_collection = db["items"]
    vendors_collection = db["vendors"]

    # Find items without location
    items_without_location = await items_collection.find(
        {
            "$or": [
                {"location": {"$exists": False}},
                {"location": None},
            ]
        }
    ).to_list(length=None)

    print(f"Found {len(items_without_location)} items without location")

    updated_count = 0
    skipped_count = 0

    for item in items_without_location:
        vendor_id = item.get("vendor_id")
        if not vendor_id:
            print(f"Item {item.get('_id')} ({item.get('name', 'N/A')}) has no vendor_id, skipping")
            skipped_count += 1
            continue

        # Get vendor location
        vendor = await vendors_collection.find_one({"_id": vendor_id})
        if not vendor:
            print(
                f"Vendor {vendor_id} not found for item {item.get('_id')} "
                f"({item.get('name', 'N/A')}), skipping"
            )
            skipped_count += 1
            continue

        vendor_location = vendor.get("location")
        if not vendor_location:
            print(
                f"Vendor {vendor_id} ({vendor.get('name', 'N/A')}) has no location "
                f"for item {item.get('_id')} ({item.get('name', 'N/A')}), skipping"
            )
            skipped_count += 1
            continue

        # Update item with vendor location
        await items_collection.update_one(
            {"_id": item["_id"]},
            {"$set": {"location": vendor_location}},
        )
        updated_count += 1
        print(
            f"✓ Updated item {item.get('_id')} ({item.get('name', 'N/A')}) "
            f"with location from vendor {vendor_id} ({vendor.get('name', 'N/A')})"
        )

    print("\n" + "=" * 60)
    print("BACKFILL SUMMARY")
    print("=" * 60)
    print(f"  - Updated: {updated_count} items")
    print(f"  - Skipped: {skipped_count} items")
    print(f"  - Total processed: {len(items_without_location)} items")


if __name__ == "__main__":
    asyncio.run(backfill_item_locations())
