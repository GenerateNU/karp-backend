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
vendor_apps = db["vendor_applications"]
org_apps = db["org_applications"]
items = db["items"]
orders = db["orders"]
events = db["events"]
volunteer_regs = db["volunteer_registrations"]

# 2. Create Vendors
vendor_docs = []
for _ in range(3):
    vendor_docs.append(
        {
            "_id": ObjectId(),
            "name": fake.company(),
            "businessType": random.choice(["Food", "Clothing", "Art"]),
            "isActive": random.choice([True, False]),
            "isApproved": random.choice([True, False]),
        }
    )
vendors.insert_many(vendor_docs)

# 3. Create Items linked to Vendors
item_docs = []
for vendor in vendor_docs:
    for _ in range(4):
        item = {
            "_id": ObjectId(),
            "name": fake.word(),
            "description": fake.sentence(),
            "price": random.randint(5, 100),
            "vendorId": vendor["_id"],
            "status": random.choice(["draft", "active", "inactive"]),
            "timePosted": datetime.utcnow(),
            "expiration": datetime.utcnow() + timedelta(days=30),
        }
        item_docs.append(item)
items.insert_many(item_docs)

# 4. Volunteers
volunteer_docs = []
for _ in range(5):
    volunteer_docs.append(
        {
            "_id": ObjectId(),
            "trainings": [random.choice(["CPR", "Safety", "FirstAid"])],
            "age": random.randint(18, 60),
            "coins": random.randint(0, 100),
            "preferences": [
                random.choice(
                    ["Animal Shelter", "Homeless Shelter", "Food Pantry", "Cleanup", "Tutoring"]
                )
            ],
            "isActive": random.choice([True, False]),
        }
    )
volunteers.insert_many(volunteer_docs)

# 5. Organizations + Events
org_docs, event_docs = [], []
for _ in range(10):
    org_id = ObjectId()
    for _ in range(5):
        ev = {
            "_id": ObjectId(),
            "name": fake.catch_phrase(),
            "location": fake.city(),
            "startDateTime": datetime.utcnow(),
            "endDateTime": datetime.utcnow() + timedelta(hours=5),
            "organizationID": org_id,
            "status": random.choice(["completed", "draft", "published", "cancelled"]),
            "maxVolunteers": 30,
            "coins": random.randint(0, 100),
        }
        event_docs.append(ev)
    org_docs.append(
        {
            "_id": org_id,
            "name": fake.company(),
            "description": fake.text(),
            "isActive": random.choice([True, False]),
            "isApproved": random.choice([True, False]),
        }
    )
organizations.insert_many(org_docs)
events.insert_many(event_docs)

volunteer_reg_docs = []
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
        volunteer_reg_docs.append(
            {
                "_id": ObjectId(),
                "eventId": event["_id"],
                "volunteerId": volunteer["_id"],
                "registeredAt": datetime.now(),
                "registrationStatus": reg_status,
                "clockedIn": clocked_in,
                "clockedOut": clocked_out,
            }
        )
volunteer_regs.insert_many(volunteer_reg_docs)

order_docs = []
for item in item_docs:
    for _ in range(5):
        volunteer = random.choice(volunteer_docs)

        order_docs.append(
            {
                "_id": ObjectId(),
                "itemId": item["_id"],
                "volunteerId": volunteer["_id"],
                "placedAt": datetime.now(),
                "orderStatus": random.choice(["pending pickup", "completed", "cancelled"]),
            }
        )
orders.insert_many(order_docs)

# 6. Memberships (AuthUser to Entities)
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
            "hashedPassword": fake.password(),
            "firstName": fake.first_name(),
            "lastName": fake.last_name(),
            "userType": entity_choice,
            "entityId": entity["_id"],
        }
    )
memberships.insert_many(membership_docs)
