"""
Karp Recommendation Algorithm Test Data Generator

This script creates a test volunteer with clear preferences and event history,
then generates upcoming events to demonstrate the recommendation algorithm.

The volunteer has:
- Preferences: Animal Shelter, Tutoring
- Completed 5 past Animal Shelter/Tutoring events at "Boston Animal Rescue"
- No current registrations (to see clean recommendations)
"""

import asyncio
import os
from datetime import datetime, timedelta

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

# Database configuration
load_dotenv()

# Database configuration
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def main():
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]

    print("=" * 80)
    print("KARP RECOMMENDATION ALGORITHM TEST DATA GENERATOR")
    print("=" * 80)

    # ============================================================================
    # STEP 0: Clean up existing test data
    # ============================================================================
    print("\n[0/7] Cleaning up existing test data...")

    # Delete test user
    user_result = await db.users.delete_many({"username": "test_volunteer_rec"})
    print(f"   ✓ Deleted {user_result.deleted_count} test user(s)")

    # Delete test organizations (and get their IDs for cascading deletes)
    test_org_names = ["Boston Animal Rescue", "Boston Food Bank"]
    test_orgs = await db.organizations.find({"name": {"$in": test_org_names}}).to_list(length=None)
    test_org_ids = [str(org["_id"]) for org in test_orgs]

    org_result = await db.organizations.delete_many({"name": {"$in": test_org_names}})
    print(f"   ✓ Deleted {org_result.deleted_count} test organization(s)")

    # Delete events created by test organizations
    if test_org_ids:
        event_result = await db.events.delete_many({"organization_id": {"$in": test_org_ids}})
        print(f"   ✓ Deleted {event_result.deleted_count} test event(s)")

    # Delete test volunteer by first_name/last_name combo
    vol_result = await db.volunteers.delete_many({"first_name": "Test", "last_name": "Volunteer"})
    print(f"   ✓ Deleted {vol_result.deleted_count} test volunteer(s)")

    # Delete registrations for test volunteer (by email pattern)
    reg_result = await db.registrations.delete_many(
        {
            "$or": [
                {
                    "volunteer_id": {
                        "$in": [
                            ObjectId(v["_id"])
                            for v in await db.volunteers.find(
                                {"first_name": "Test", "last_name": "Volunteer"}
                            ).to_list(length=None)
                        ]
                    }
                },
            ]
        }
    )
    print(f"   ✓ Deleted {reg_result.deleted_count} test registration(s)")

    print("   ✓ Cleanup complete\n")

    # ============================================================================
    # STEP 1: Create Test Organization
    # ============================================================================
    print("\n[1/7] Creating test organization...")

    org_id = ObjectId()
    test_org = {
        "_id": org_id,
        "name": "Boston Animal Rescue",
        "description": "Dedicated to rescuing and rehoming animals in the Boston area",
        "address": "123 Commonwealth Ave, Boston, MA 02116",
        "status": "APPROVED",
        "location": {
            "type": "Point",
            "coordinates": [-71.0942, 42.3505],  # Commonwealth Ave, Boston
        },
    }
    await db.organizations.insert_one(test_org)
    print(f"   ✓ Created organization: {test_org['name']} (ID: {org_id})")

    # Create a second organization for low-match events
    org_id_2 = ObjectId()
    test_org_2 = {
        "_id": org_id_2,
        "name": "Boston Food Bank",
        "description": "Fighting hunger in Boston communities",
        "address": "70 South Bay Ave, Boston, MA 02118",
        "status": "APPROVED",
        "location": {
            "type": "Point",
            "coordinates": [-71.0632, 42.3398],  # South Bay, Boston
        },
    }
    await db.organizations.insert_one(test_org_2)
    print(f"   ✓ Created organization: {test_org_2['name']} (ID: {org_id_2})")

    # ============================================================================
    # STEP 2: Create Test User
    # ============================================================================
    print("\n[2/7] Creating test user...")

    user_id_obj = ObjectId()
    user_id = str(user_id_obj)  # String for 'id' field
    volunteer_id = ObjectId()

    test_user = {
        "_id": user_id_obj,  # ObjectId for _id
        "email": "test.rec@example.com",  # Changed to valid domain
        "username": "test_volunteer_rec",
        "hashed_password": pwd_context.hash("TestRec123!"),
        "first_name": "Test",
        "last_name": "Volunteer",
        "user_type": "VOLUNTEER",
        "entity_id": str(volunteer_id),
    }

    try:
        await db.users.update_one({"_id": user_id_obj}, {"$set": {"id": user_id}})

        print(f"   ✓ Created user: {test_user['username']}")
        print(f"   📧 Email: {test_user['email']}")
        print("   🔑 Password: TestRec123!")
        print(f"   🆔 User ID: {user_id}")

        # Verify user was created with both fields
        verify_user = await db.users.find_one({"username": "test_volunteer_rec"})
        if verify_user:
            print("   ✅ Verified user exists in database")
            print(f"   ✅ Has 'id' field: {'id' in verify_user}")
            print(f"   ✅ Has '_id' field: {'_id' in verify_user}")
            if "id" in verify_user:
                print(f"   ✅ id value: {verify_user['id']}")
        else:
            print("   ❌ ERROR: User not found in database after insert!")

    except Exception as e:
        print(f"   ❌ Error creating user: {e}")
        raise

    # ============================================================================
    # STEP 3: Create Test Volunteer
    # ============================================================================
    print("\n[3/7] Creating test volunteer...")

    test_volunteer = {
        "_id": volunteer_id,
        "first_name": "Test",
        "last_name": "Volunteer",
        "coins": 500,
        "preferred_name": "Tester",
        "birth_date": datetime(2000, 1, 1),
        "preferences": ["Animal Shelter", "Tutoring"],  # Clear preferences
        "training_documents": [],
        "qualifications": ["CPR Certified", "Multilingual"],
        "preferred_days": ["Saturday", "Sunday"],
        "is_active": True,
        "experience": 150,
        "current_level": 3,
        "location": {
            "type": "Point",
            "coordinates": [-71.0942, 42.3505],  # Boston
        },
    }
    await db.volunteers.insert_one(test_volunteer)
    print(f"   ✓ Created volunteer: {test_volunteer['first_name']} {test_volunteer['last_name']}")
    print(f"   ✓ Preferences: {test_volunteer['preferences']}")
    print(f"   ✓ Volunteer ID: {volunteer_id}")

    # ============================================================================
    # STEP 4: Create Past Events (Completed)
    # ============================================================================
    print("\n[4/7] Creating past completed events...")

    past_events = []
    base_date = datetime.now() - timedelta(days=30)

    past_event_data = [
        {
            "name": "Weekend Dog Walking",
            "description": "Help walk shelter dogs at Boston Animal Rescue",
            "tags": ["Animal Shelter"],
            "address": "123 Commonwealth Ave, Boston, MA 02116",
            "hours": 3,
        },
        {
            "name": "Cat Adoption Fair",
            "description": "Assist with cat adoption event",
            "tags": ["Animal Shelter"],
            "address": "123 Commonwealth Ave, Boston, MA 02116",
            "hours": 4,
        },
        {
            "name": "Animal Shelter Cleanup",
            "description": "Deep clean animal shelter facilities",
            "tags": ["Animal Shelter", "Cleanup"],
            "address": "123 Commonwealth Ave, Boston, MA 02116",
            "hours": 2,
        },
        {
            "name": "Math Tutoring for Kids",
            "description": "Help elementary students with math homework",
            "tags": ["Tutoring"],
            "address": "456 Beacon St, Boston, MA 02115",
            "hours": 2,
        },
        {
            "name": "Reading Buddies",
            "description": "Read with children at community center",
            "tags": ["Tutoring"],
            "address": "789 Boylston St, Boston, MA 02116",
            "hours": 3,
        },
    ]

    for i, event_data in enumerate(past_event_data):
        event_id = ObjectId()
        start_time = base_date + timedelta(days=i * 3)
        end_time = start_time + timedelta(hours=event_data["hours"])

        event = {
            "_id": event_id,
            "name": event_data["name"],
            "address": event_data["address"],
            "location": {
                "type": "Point",
                "coordinates": [-71.0942, 42.3505],
            },
            "start_date_time": start_time,
            "end_date_time": end_time,
            "organization_id": str(org_id),
            "status": "APPROVED",  # Keep as APPROVED so similarities are computed
            "max_volunteers": 20,
            "description": event_data["description"],
            "keywords": event_data["tags"],
            "tags": event_data["tags"],
            "age_min": 16,
            "age_max": None,
            "created_at": datetime.now(),
            "created_by": str(user_id),
            "coins": event_data["hours"] * 100,
            "manual_difficulty_coefficient": 1.0,
            "ai_difficulty_coefficient": 1.0,
            "difficulty_coefficient": 1.0,
        }

        await db.events.insert_one(event)
        past_events.append(event)
        print(f"   ✓ Created past event: {event['name']} ({', '.join(event['tags'])})")

        # Create completed registration
        registration = {
            "_id": ObjectId(),
            "event_id": event_id,
            "volunteer_id": volunteer_id,
            "registered_at": start_time - timedelta(days=2),
            "registration_status": "completed",
            "clocked_in": start_time,
            "clocked_out": end_time,
        }
        await db.registrations.insert_one(registration)

    print(f"   ✓ Created {len(past_events)} completed registrations")

    # ============================================================================
    # STEP 5: Create Upcoming Events (Mixed Recommendations)
    # ============================================================================
    print("\n[5/7] Creating upcoming events...")

    upcoming_events = []
    future_base = datetime.now() + timedelta(days=7)

    # HIGH MATCH EVENTS (Animal Shelter + Tutoring, same org)
    high_match_events = [
        {
            "name": "Puppy Socialization Session",
            "description": "Help socialize puppies for adoption",
            "tags": ["Animal Shelter"],
            "org_id": org_id,
            "address": "123 Commonwealth Ave, Boston, MA 02116",
            "hours": 2,
            "expected_score": "HIGH (collab + content match)",
        },
        {
            "name": "SAT Prep Tutoring",
            "description": "Tutor high school students for SAT",
            "tags": ["Tutoring"],
            "org_id": org_id,
            "address": "123 Commonwealth Ave, Boston, MA 02116",
            "hours": 3,
            "expected_score": "HIGH (collab + content match)",
        },
        {
            "name": "Pet Therapy Training",
            "description": "Train volunteers for animal therapy programs",
            "tags": ["Animal Shelter", "Tutoring"],
            "org_id": org_id,
            "address": "123 Commonwealth Ave, Boston, MA 02116",
            "hours": 4,
            "expected_score": "VERY HIGH (both tags match)",
        },
    ]

    # MEDIUM MATCH EVENTS (Same org, different tags)
    medium_match_events = [
        {
            "name": "Community Garden Cleanup",
            "description": "Help clean and maintain community garden",
            "tags": ["Cleanup"],
            "org_id": org_id,
            "address": "123 Commonwealth Ave, Boston, MA 02116",
            "hours": 3,
            "expected_score": "MEDIUM (org match only)",
        },
        {
            "name": "Food Pantry Sorting",
            "description": "Sort and organize donated food items",
            "tags": ["Food Pantry"],
            "org_id": org_id,
            "address": "123 Commonwealth Ave, Boston, MA 02116",
            "hours": 2,
            "expected_score": "MEDIUM (org match only)",
        },
    ]

    # LOW MATCH EVENTS (Different org, different tags)
    low_match_events = [
        {
            "name": "Soup Kitchen Service",
            "description": "Serve meals at community soup kitchen",
            "tags": ["Food Pantry"],
            "org_id": org_id_2,
            "address": "70 South Bay Ave, Boston, MA 02118",
            "hours": 3,
            "expected_score": "LOW (no match)",
        },
        {
            "name": "Homeless Shelter Overnight",
            "description": "Staff overnight shift at homeless shelter",
            "tags": ["Homeless Shelter"],
            "org_id": org_id_2,
            "address": "70 South Bay Ave, Boston, MA 02118",
            "hours": 8,
            "expected_score": "LOW (no match)",
        },
    ]

    all_upcoming = high_match_events + medium_match_events + low_match_events

    for i, event_data in enumerate(all_upcoming):
        event_id = ObjectId()
        start_time = future_base + timedelta(days=i * 2, hours=10)
        end_time = start_time + timedelta(hours=event_data["hours"])

        event = {
            "_id": event_id,
            "name": event_data["name"],
            "address": event_data["address"],
            "location": {
                "type": "Point",
                "coordinates": [-71.0942, 42.3505],
            },
            "start_date_time": start_time,
            "end_date_time": end_time,
            "organization_id": str(event_data["org_id"]),
            "status": "APPROVED",
            "max_volunteers": 25,
            "description": event_data["description"],
            "keywords": event_data["tags"],
            "tags": event_data["tags"],
            "age_min": 16,
            "age_max": None,
            "created_at": datetime.now(),
            "created_by": str(user_id),
            "coins": event_data["hours"] * 100,
            "manual_difficulty_coefficient": 1.0,
            "ai_difficulty_coefficient": 1.0,
            "difficulty_coefficient": 1.0,
        }

        await db.events.insert_one(event)
        upcoming_events.append({**event, "expected_score": event_data["expected_score"]})
        print(
            f"   ✓ {event['name']} - Tags: {', '.join(event['tags'])} - "
            f"Expected: {event_data['expected_score']}"
        )

    # ============================================================================
    # STEP 6: Compute Event Similarities
    # ============================================================================
    print("\n[6/7] Computing event similarities...")

    # Import the recommendation service to compute similarities
    # Note: You'll need to adjust the import path based on your project structure
    try:
        from app.services.recommendation import recommendation_service

        # Get all events (past + upcoming) to compute similarities
        all_test_events = []
        for event_doc in past_events + [e for e in upcoming_events]:
            # Convert to Event schema
            from app.schemas.event import Event

            event_obj = Event(**event_doc)
            all_test_events.append(event_obj)

        # Compute similarities
        similarities = await recommendation_service.compute_event_similarities(all_test_events)

        # Store similarities
        from app.models.event_similarity import event_similarity_model

        for event_id_str, similar_events in similarities.items():
            if similar_events:
                await event_similarity_model.upsert_similarities(event_id_str, similar_events)

        print(f"   ✓ Computed similarities for {len(similarities)} events")

    except Exception as e:
        print(f"   ⚠ Could not compute similarities (run manually): {e}")
        print("   → You can run the similarity computation script separately")

    # ============================================================================
    # STEP 7: Calculate Expected Recommendations
    # ============================================================================
    print("\n[7/7] Calculating expected recommendation scores...")
    print("\n" + "=" * 80)
    print("EXPECTED RECOMMENDATIONS (Sorted by Score)")
    print("=" * 80)

    # Manually calculate expected scores based on algorithm
    # Algorithm: 70% collaborative filtering + 30% content-based filtering

    # For this volunteer:
    # - Completed events: All have Animal Shelter OR Tutoring tags
    # - Preferences: Animal Shelter, Tutoring

    print("\n📊 SCORING BREAKDOWN:")
    print(
        "\nAlgorithm: Hybrid (70% Collaborative Filtering + 30% Content-Based)\n"
        "- Collaborative: Similarity to completed events (via event_similarities)\n"
        "- Content-Based: Tag overlap with volunteer preferences\n"
    )

    print("\n🔥 HIGH SCORE EVENTS (Should appear first):")
    print("   1. Pet Therapy Training")
    print("      Tags: Animal Shelter, Tutoring (BOTH match preferences)")
    print("      Org: Boston Animal Rescue (same as past events)")
    print("      Content Score: 2/2 = 1.0")
    print("      Collab Score: High (similar to past Animal Shelter events)")
    print("      Final: ~0.85-0.95\n")

    print("   2. Puppy Socialization Session")
    print("      Tags: Animal Shelter (matches 1/2 preferences)")
    print("      Org: Boston Animal Rescue (same)")
    print("      Content Score: 1/2 = 0.5")
    print("      Collab Score: High (similar to past Animal Shelter events)")
    print("      Final: ~0.60-0.75\n")

    print("   3. SAT Prep Tutoring")
    print("      Tags: Tutoring (matches 1/2 preferences)")
    print("      Org: Boston Animal Rescue (same)")
    print("      Content Score: 1/2 = 0.5")
    print("      Collab Score: High (similar to past Tutoring events)")
    print("      Final: ~0.60-0.75\n")

    print("\n📉 MEDIUM SCORE EVENTS:")
    print("   4. Community Garden Cleanup")
    print("      Tags: Cleanup (no preference match)")
    print("      Org: Boston Animal Rescue (same)")
    print("      Content Score: 0/2 = 0.0")
    print("      Collab Score: Low (only org similarity)")
    print("      Final: ~0.10-0.30\n")

    print("   5. Food Pantry Sorting")
    print("      Tags: Food Pantry (no preference match)")
    print("      Org: Boston Animal Rescue (same)")
    print("      Content Score: 0/2 = 0.0")
    print("      Collab Score: Low (only org similarity)")
    print("      Final: ~0.10-0.30\n")

    print("\n❄️  LOW SCORE EVENTS (Should appear last):")
    print("   6. Soup Kitchen Service")
    print("      Tags: Food Pantry (no match)")
    print("      Org: Boston Food Bank (different)")
    print("      Content Score: 0/2 = 0.0")
    print("      Collab Score: ~0.0 (no similarity)")
    print("      Final: ~0.0-0.10\n")

    print("   7. Homeless Shelter Overnight")
    print("      Tags: Homeless Shelter (no match)")
    print("      Org: Boston Food Bank (different)")
    print("      Content Score: 0/2 = 0.0")
    print("      Collab Score: ~0.0 (no similarity)")
    print("      Final: ~0.0-0.10\n")

    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("\n" + "=" * 80)
    print("✅ TEST DATA CREATION COMPLETE")
    print("=" * 80)
    print("\n📝 Summary:")
    print("   • Test User Created: test_volunteer_rec / TestRec123!")
    print(f"   • User ID: {user_id}")
    print(f"   • Volunteer ID: {volunteer_id}")
    print("   • Organizations: 2 (Boston Animal Rescue, Boston Food Bank)")
    print(f"   • Past Completed Events: {len(past_events)}")
    print(f"   • Upcoming Events: {len(upcoming_events)}")
    print("   • Event Similarities: Computed")

    print("\n🧪 TO TEST:")
    print("   1. Login with: test_volunteer_rec / TestRec123!")
    print("   2. Navigate to Events tab")
    print("   3. Click 'Recommendations' sort option")
    print("   4. Verify events appear in expected order (high → low scores)")

    print(
        "\n💡 TIP: Use the /recommendation/events/scores endpoint to see actual scores:\n"
        "   GET http://localhost:8080/recommendation/events/scores"
    )

    print("\n" + "=" * 80)

    # FINAL VERIFICATION - Check if data persists
    print("\n🔍 FINAL VERIFICATION:")
    final_user = await db.users.find_one({"username": "test_volunteer_rec"})
    final_volunteer = await db.volunteers.find_one({"_id": volunteer_id})
    final_orgs = await db.organizations.find(
        {"name": {"$in": ["Boston Animal Rescue", "Boston Food Bank"]}}
    ).to_list(length=None)

    print(f"   User exists: {final_user is not None}")
    print(f"   Volunteer exists: {final_volunteer is not None}")
    print(f"   Organizations exist: {len(final_orgs)}")

    if final_user:
        print("   ✅ User document structure:")
        print(f"      - _id: {final_user.get('_id')}")
        print(f"      - id: {final_user.get('id')}")
        print(f"      - username: {final_user.get('username')}")
        print(f"      - entity_id: {final_user.get('entity_id')}")

    # Close client properly
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
