import random
from datetime import datetime, timedelta

from bson import ObjectId
from faker import Faker
from pymongo import MongoClient

from app.core.config import settings

fake = Faker()
connection_string = settings.MONGODB_URL


client = MongoClient(connection_string)
db = client["small_mock_db"]

# Collections
memberships = db["memberships"]
vendors = db["vendors"]
volunteers = db["volunteers"]
organizations = db["organizations"]
admins = db["admins"]
items = db["items"]
orders = db["orders"]
events = db["events"]
registrations = db["registrations"]

# Create Vendors
vendor_docs = []
for _ in range(3):
    vendor_docs.append(
        {
            "_id": ObjectId(),
            "name": fake.company(),
            "business_type": random.choice(["Food", "Clothing", "Art"]),
            "status": random.choice(
                ["approved", "in review", "rejected", "deleted"]
            ),  # NEW: have a status enum with approved, in review, rejected, deleted
        }
    )
vendors.insert_many(vendor_docs)

# Create Items linked to Vendors
item_docs = []
for vendor in vendor_docs:
    for _ in range(4):
        item = {
            "_id": ObjectId(),
            "name": fake.word(),
            "description": fake.sentence(),
            "price": random.randint(5, 100),
            "vendor_id": vendor["_id"],
            "status": random.choice(["draft", "active", "inactive"]),
            "time_posted": datetime.utcnow(),
            "expiration": datetime.utcnow() + timedelta(days=30),
        }
        item_docs.append(item)
items.insert_many(item_docs)

# Create Volunteers
volunteer_docs = []
for _ in range(5):
    volunteer_docs.append(
        {
            "_id": ObjectId(),
            "age": random.randint(18, 60),
            "coins": random.randint(0, 100),
            "preferences": [
                random.choice(
                    ["Animal Shelter", "Homeless Shelter", "Food Pantry", "Cleanup", "Tutoring"]
                )
            ],
            "is_active": random.choice([True, False]),
        }
    )
volunteers.insert_many(volunteer_docs)

# Create Organizations + Events
org_docs, event_docs = [], []
for _ in range(10):
    org_id = ObjectId()
    for _ in range(5):
        ev = {
            "_id": ObjectId(),
            "name": fake.catch_phrase(),
            "location": fake.city(),
            "start_date_time": datetime.utcnow(),
            "end_date_time": datetime.utcnow() + timedelta(hours=5),
            "organization_id": org_id,
            "status": random.choice(
                ["COMPLETED", "DRAFT", "PUBLISHED", "CANCELLED", "DELETED"]
            ),  # NEW: add deleted
            "max_volunteers": 30,
            "coins": random.randint(0, 100),
        }
        event_docs.append(ev)
    org_docs.append(
        {
            "_id": org_id,
            "name": fake.company(),
            "description": fake.text(),
            "status": random.choice(
                ["APPROVED", "PENDING", "REJECTED", "DELETED"]
            ),  # NEW: have a status enum with approved, in review, rejected, deleted
        }
    )
organizations.insert_many(org_docs)
events.insert_many(event_docs)

# Volunteer Registration
registration_docs = []
for event in event_docs:
    for _ in range(5):
        volunteer = random.choice(volunteer_docs)
        reg_status = random.choice(["upcoming", "completed", "incompleted"])
        if reg_status == "upcoming":
            clocked_in, clocked_out = False, False
        elif reg_status == "completed":
            clocked_in, clocked_out = True, True
        else:
            clocked_in, clocked_out = True, False
        registration_docs.append(
            {
                "_id": ObjectId(),
                "event_id": event["_id"],
                "volunteer_id": volunteer["_id"],
                "registered_at": datetime.now(),
                "registration_status": reg_status,
                "clocked_in": clocked_in,
                "clocked_out": clocked_out,
            }
        )
registrations.insert_many(registration_docs)

# Create Orders
order_docs = []
for item in item_docs:
    for _ in range(5):
        volunteer = random.choice(volunteer_docs)

        order_docs.append(
            {
                "_id": ObjectId(),
                "item_id": item["_id"],
                "volunteer_id": volunteer["_id"],
                "placed_at": datetime.now(),
                "order_status": random.choice(["pending pickup", "completed", "cancelled"]),
            }
        )
orders.insert_many(order_docs)

# Create Memberships
membership_docs = []
for _ in range(20):
    entity_choice = random.choice(["vendor", "volunteer", "organization"])
    if entity_choice == "vendor":
        entity = random.choice(vendor_docs)
    elif entity_choice == "volunteer":
        entity = random.choice(volunteer_docs)
    else:
        entity = random.choice(org_docs)
    membership_docs.append(
        {
            "_id": ObjectId(),
            "email": fake.email(),
            "username": fake.user_name(),
            "hashed_password": fake.password(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "user_type": entity_choice,
            "entity_id": entity["_id"],
        }
    )
memberships.insert_many(membership_docs)
