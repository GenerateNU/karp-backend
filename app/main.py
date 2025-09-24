from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import (
    event,
    health,
    item,
    organization,
    registration,
    user,
    vendor,
    volunteer,
)

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost",
    "http://192.168.1.34:8000",
    "http://localhost:8000",
    "http://localhost:3000",  # Add your frontend URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="", tags=["health"])

app.include_router(user.router, prefix="/users", tags=["users"])

app.include_router(item.router, prefix="/items", tags=["items"])

app.include_router(vendor.router, prefix="/vendors", tags=["vendors"])

app.include_router(organization.router, prefix="/organizations", tags=["organizations"])

app.include_router(event.router, prefix="/events", tags=["events"])

app.include_router(volunteer.router, prefix="/volunteers", tags=["volunteers"])

app.include_router(registration.router, prefix="/registrations", tags=["registrations"])
