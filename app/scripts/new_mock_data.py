import random

import requests
from faker import Faker

fake = Faker()
register_user_url = "http://localhost:8080/user/"
sign_in_user_url = "http://localhost:8080/user/token"
get_me_url = "http://localhost:8080/user/me"
create_new_volunteer_url = "http://localhost:8080/volunteer/new"
create_new_org_url = "http://localhost:8080/organization/new"
create_new_event_url = "http://localhost:8080/event/new"
create_new_vendor_url = "http://localhost:8080/vendor/new"
create_new_item_url = "http://localhost:8080/item/new"
get_orgs_url = "http://localhost:8080/organization/all"
create_new_order_url = "http://localhost:8080/order/new"
create_new_registration_url = "http://localhost:8080/registration/new"
item_ids = [
    "68e1d1c5c320a33ba155f260",
    "68e1d1c6c320a33ba155f264",
    "68e1d1c7c320a33ba155f268",
    "68e1d1c7c320a33ba155f26c",
    "68e1d1c8c320a33ba155f270",
]
event_ids = [
    "68e4774368a5c39282e7a9b7",
    "68e4774468a5c39282e7a9bb",
    "68e4774568a5c39282e7a9bf",
    "68e4774668a5c39282e7a9c3",
    "68e4774768a5c39282e7a9c7",
]
for _ in range(10):
    username = fake.user_name()
    password = fake.password()
    first_name = fake.first_name()
    last_name = fake.last_name()
    register_payload = {
        "email": fake.email(),
        "username": username,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "user_type": "VOLUNTEER",
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(register_user_url, json=register_payload, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.json())
    if response.status_code == 200:
        sign_in_payload = {"username": username, "password": password}
        headers = {"Content-Type": "application/json"}
        response = requests.post(sign_in_user_url, json=sign_in_payload, headers=headers)
        print("Status:", response.status_code)
        print("Response:", response.json())
        if response.status_code == 200:
            bearer_token = response.json()["access_token"]
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {bearer_token}",
            }
            response = requests.get(get_me_url, headers=headers)
            print("Status:", response.status_code)
            print("Response:", response.json())
            if response.status_code == 200:
                create_user_payload = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "age": random.randint(18, 60),
                    "coins": random.randint(18, 300),
                    "preferences": [
                        random.choice(
                            [
                                "Animal Shelter",
                                "Homeless Shelter",
                                "Food Pantry",
                                "Cleanup",
                                "Tutoring",
                            ]
                        )
                    ],
                    "location": {
                        "type": "Point",  # usually "Point" for GeoJSON-style data
                        "coordinates": [fake.longitude(), fake.latitude()],
                    },
                }
                # create_vendor_payload = {
                #     "name": fake.company(),
                #     "business_type": random.choice(["Food", "Clothing", "Art"]),
                # }
                # create_org_payload = {
                #     "name": fake.company(),
                #     "description": fake.sentence(),
                # }
                # create_order_payload = {
                #     "item_id" : random.choice(item_ids)
                # }
                response = requests.post(
                    create_new_volunteer_url, json=create_user_payload, headers=headers
                )
                print("Status:", response.status_code)
                print("Response:", response.json())
                if response.status_code == 200:
                    # create_item_payload = {
                    #     "name": fake.catch_phrase(),
                    #     "expiration": "2025-10-05T01:44:05.756Z",
                    # }

                    #     create_event_payload = {
                    #         "name": fake.catch_phrase(),
                    #         "address": fake.address(),
                    #         "location": {
                    #             "type": "Point",  # usually "Point" for GeoJSON-style data
                    #             "coordinates": [fake.longitude(), fake.latitude()],
                    #         },
                    #         "start_date_time": "2025-10-04T23:55:06.429Z",
                    #         "end_date_time": "2025-10-04T23:58:06.550Z",
                    #         "max_volunteers": random.randint(1, 300),
                    #         "coins": random.randint(1, 500),
                    #         "tags": [
                    #             random.choice(
                    #                 [
                    #                     "Animal Shelter",
                    #                     "Homeless Shelter",
                    #                     "Food Pantry",
                    #                     "Cleanup",
                    #                     "Tutoring",
                    #                 ]
                    #             )
                    #         ],
                    #     }

                    # create_order_payload = {
                    #     "item_id" : random.choice(item_ids)
                    # }
                    create_registration_payload = {"event_id": random.choice(event_ids)}
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {bearer_token}",
                    }
                    response = requests.post(
                        create_new_registration_url,
                        json=create_registration_payload,
                        headers=headers,
                    )
                    print("Status:", response.status_code)
                    # print("Response:", response.json())


# bearer_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ2ZXJ
# vbmljYWJyb3duQGV4YW1wbGUub3JnIiwiZXhwIjoxNzU5NjQwODM2fQ
# .iPrOte0pGb7eJR0wiLtMu-S9eSZBcimA9gBDvWgVRek"
# headers = {
#                 "Content-Type": "application/json",
#                 "Authorization": f"Bearer {bearer_token}"
#             }
# organizations = requests.get(get_orgs_url, headers=headers)
# create_event_payload = {
#     "name": fake.catch_phrase(),
#     "address": fake.address(),
#     "location": {
#         "type": "Point",  # usually "Point" for GeoJSON-style data
#         "coordinates": [fake.longitude(), fake.latitude()]
#     },
#     "start_date_time": "2025-10-04T23:55:06.429Z",
#     "end_date_time": "2025-10-04T23:58:06.550Z",
#     "max_volunteers": random.randint(1, 300),
#     "coins": random.randint(1, 500),
#     "tags": [
#         random.choice(
#             ["Animal Shelter", "Homeless Shelter", "Food Pantry", "Cleanup", "Tutoring"]
#         )
#     ],
# }
# headers = {
#                 "Content-Type": "application/json",
#                 "Authorization": f"Bearer {bearer_token}"
#             }
# response = requests.post(create_new_event_url, json=create_event_payload, headers=headers)
# print("Status:", response.status_code)
# print("Response:", response.json())
