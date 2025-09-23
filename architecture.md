# Architecture

There are usually three main layers: 
- Route (or Controller)
- Service
- Model 

## Route / Controller Layer

- Purpose: Handles HTTP requests and responses, Calls the service layer for processing, Returns validated responses 

## Service Layer

- Purpose: Encapsulates business logic
- The service layer sits between routes and models.
- Handles things like: Complex Validations, Checking permissions or ownership

## Model Layer

- Responsible for defining data structures and interacting with the db (queries)