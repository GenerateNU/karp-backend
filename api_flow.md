# Testing The API Flow

We want to guard our backend APIs with auth. To do this, we decorate our API endpoints with Depends(get_current_user), which forces a user to be signed in (otherwise it will throw 401). Below is a simple flow for testing an auth-guarded endpoint.

- Import this as ```Register User``` into Postman and hit it (or change email as needed if it has already been registered)
```
curl --location 'http://localhost:8080/users' \
--header 'Content-Type: application/json' \
--header 'Cookie: kl_csrftoken=lJUhDl0Lffqes6OKO3feS5UCry9xG3bA' \
--data-raw '{
    "username": "Test3",
    "email": "test3@gmail.com",
    "password": "TestPassword_123!",
    "first_name": "Test3",
    "last_name": "Test3",
    "user_type": "VENDOR"
}'
```

- Import this as ```Sign In User``` into Postman, hit it, and copy the ```access_token``` from the response payload
```
curl --location 'http://localhost:8080/users/token' \
--header 'Content-Type: application/json' \
--header 'Cookie: kl_csrftoken=lJUhDl0Lffqes6OKO3feS5UCry9xG3bA' \
--data '{
    "username": "Test3",
    "password": "TestPassword_123!"
}'
```

- Import this as ```Get Me``` into Postman, go to the Authorization tab, select Bearer, replace with the value you copied from before, and hit it (you should get null for the ```entity_id```)
```
curl --location 'http://localhost:8080/users/me' \
--header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0M0BnbWFpbC5jb20iLCJleHAiOjE3NTgxMDIxNDl9.kS98F14s9xejZ8OKyc9Xyr1TyGLrYgTA-MpWpbaDksI' \
--header 'Cookie: kl_csrftoken=lJUhDl0Lffqes6OKO3feS5UCry9xG3bA'
```

- Import this as ```Create New Vendor``` into Postman, replace the bearer token like above, and hit it
```
curl --location 'http://localhost:8080/vendors/new' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0M0BnbWFpbC5jb20iLCJleHAiOjE3NTgxMDExMzN9.FSFC-DUfVghsNmjgRlfMrZ22Q1917AwOx6MCK_Uuyp0' \
--header 'Cookie: kl_csrftoken=lJUhDl0Lffqes6OKO3feS5UCry9xG3bA' \
--data '{
    "name": "Vendor",
    "business_type": "Clothing"
}
'
```

- Hit the ```Get Me``` endpoint again, and this time the ```entity_id``` should be set