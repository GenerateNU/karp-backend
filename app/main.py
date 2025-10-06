from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import (
    achievement,
    admin,
    event,
    health,
    item,
    order,
    organization,
    registration,
    user,
    vendor,
    volunteer,
    volunteer_achievement,
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

app.include_router(user.router, prefix="/user", tags=["user"])

app.include_router(admin.router, prefix="/admin", tags=["admin"])

app.include_router(item.router, prefix="/item", tags=["item"])

app.include_router(vendor.router, prefix="/vendor", tags=["vendor"])

app.include_router(organization.router, prefix="/organization", tags=["organization"])

app.include_router(event.router, prefix="/event", tags=["event"])

app.include_router(volunteer.router, prefix="/volunteer", tags=["volunteer"])

app.include_router(
    registration.router, prefix="/volunteer-registration", tags=["volunteer-registration"]
)

app.include_router(achievement.router, prefix="/achievement", tags=["achievement"])

app.include_router(
    volunteer_achievement.router, prefix="/volunteer-achievement", tags=["volunteer-achievement"]
)

app.include_router(registration.router, prefix="/registration", tags=["registration"])

app.include_router(order.router, prefix="/order", tags=["order"])
