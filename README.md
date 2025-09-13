# Karp Backend

This is the repository for all backend services for Karp, including those related to the customer facing mobile app, those related to the organization/vendor facing web app, as well as those related to the admin facing internal tool

We are using Python FastAPI

# Setup Instructions

1. Install ```Python 3.13.3``` (or similar version) at the root level of your laptop
2. Run ```python3 -m venv venv```
3. Run ```source venv/bin/activate```
4. Run ```pip install -r requirements.txt```
5. ```Cmd + Shift + P``` > ```Python: Select Interpreter``` > ```Enter interpreter path...``` > ```./venv/bin/python```
6. Make an ```.env``` file at the root level
7. Set the values for the variables ```MONGODB_URL``` (should be the connection string with <db_password> replaced by the password that Sierra will give you) and ```ACCESS_TOKEN_EXPIRE_MINUTES``` (300 is fine for now)
8. Run ```python run.py```
9. Install Postman
10. Make a new tab, and send a GET request to ```http://localhost:8080``` and ensure that the returned result is ```{ "status": "ok", "message": "API is running" }```
11. Make a MongoDB account and get Sierra to add you to the list of users by providing you an email
12. Run ```pre-commit install```