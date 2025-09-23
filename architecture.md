## Common architecture in FastAPI 
There are usually three main layers: 
- Route (or Controller)
- Service
- Model 

1. Route / Controller Layer

Purpose: Handles HTTP requests and responses, Calls the service layer for processing, Returns validated responses 

2. Service Layer

Purpose: Encapsulates business logic

The service layer sits between routes and models.

Handles things like: Complex Validations, Checking permissions or ownership

3. Model Layer

Responsible for defining data structures and interacting with the db (queries)

