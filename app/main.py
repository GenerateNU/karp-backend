from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import health, item, organizations, users, vendors

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

# Include the users router
app.include_router(health.router, prefix="", tags=["health"])

app.include_router(users.router, prefix="/users", tags=["users"])

app.include_router(item.router, prefix="/item", tags=["item"])

app.include_router(vendors.router, prefix="/vendors", tags=["vendors"])

app.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
