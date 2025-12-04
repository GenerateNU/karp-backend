"""
Script to check if vendors and items have locations in the database.
Run this to diagnose location filtering issues.
"""

import asyncio

from app.database.mongodb import db


async def check_locations():
    """Check the location status of vendors and items."""
    vendors_collection = db["vendors"]
    items_collection = db["items"]

    # Check vendors
    total_vendors = await vendors_collection.count_documents({})
    vendors_with_location = await vendors_collection.count_documents(
        {"location": {"$exists": True, "$ne": None}}
    )
    vendors_without_location = total_vendors - vendors_with_location

    print("=" * 60)
    print("VENDOR LOCATION STATUS")
    print("=" * 60)
    print(f"Total vendors: {total_vendors}")
    print(f"Vendors WITH location: {vendors_with_location}")
    print(f"Vendors WITHOUT location: {vendors_without_location}")

    if vendors_without_location > 0:
        print("\nVendors without location:")
        vendors_no_loc = await vendors_collection.find(
            {
                "$or": [
                    {"location": {"$exists": False}},
                    {"location": None},
                ]
            },
            {"_id": 1, "name": 1, "address": 1},
        ).to_list(length=10)
        for vendor in vendors_no_loc:
            print(f"  - {vendor.get('_id')}: {vendor.get('name')} ({vendor.get('address', 'N/A')})")

    # Check items
    total_items = await items_collection.count_documents({})
    items_with_location = await items_collection.count_documents(
        {"location": {"$exists": True, "$ne": None}}
    )
    items_without_location = total_items - items_with_location

    print("\n" + "=" * 60)
    print("ITEM LOCATION STATUS")
    print("=" * 60)
    print(f"Total items: {total_items}")
    print(f"Items WITH location: {items_with_location}")
    print(f"Items WITHOUT location: {items_without_location}")

    if items_without_location > 0:
        print("\nItems without location (first 10):")
        items_no_loc = await items_collection.find(
            {
                "$or": [
                    {"location": {"$exists": False}},
                    {"location": None},
                ]
            },
            {"_id": 1, "name": 1, "vendor_id": 1},
        ).to_list(length=10)
        for item in items_no_loc:
            vendor_id = item.get("vendor_id")
            # Check if vendor has location
            vendor = await vendors_collection.find_one(
                {"_id": vendor_id}, {"location": 1, "name": 1}
            )
            vendor_has_loc = vendor and vendor.get("location")
            print(
                f"  - {item.get('_id')}: {item.get('name')} "
                f"(vendor: {vendor_id}, vendor has location: {vendor_has_loc})"
            )

    # Check items that should have location (vendor has location but item doesn't)
    print("\n" + "=" * 60)
    print("ITEMS THAT SHOULD HAVE LOCATION (vendor has location)")
    print("=" * 60)
    items_no_loc_cursor = items_collection.find(
        {
            "$or": [
                {"location": {"$exists": False}},
                {"location": None},
            ]
        },
        {"_id": 1, "name": 1, "vendor_id": 1},
    )
    items_to_fix = []
    async for item in items_no_loc_cursor:
        vendor_id = item.get("vendor_id")
        if vendor_id:
            vendor = await vendors_collection.find_one(
                {"_id": vendor_id}, {"location": 1, "name": 1}
            )
            if vendor and vendor.get("location"):
                items_to_fix.append((item.get("_id"), item.get("name"), vendor_id))

    print(f"Found {len(items_to_fix)} items that should have location:")
    for item_id, item_name, vendor_id in items_to_fix[:10]:
        print(f"  - {item_id}: {item_name} (vendor: {vendor_id})")
    if len(items_to_fix) > 10:
        print(f"  ... and {len(items_to_fix) - 10} more")


if __name__ == "__main__":
    asyncio.run(check_locations())
