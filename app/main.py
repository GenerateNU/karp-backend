from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.endpoints import (
    achievement,
    admin,
    device_token,
    event,
    geocoding,
    health,
    item,
    order,
    organization,
    recommendation,
    registration,
    user,
    vendor,
    volunteer,
    volunteer_achievement,
)
from app.core.config import settings
from app.models.event import EventModel
from app.models.event_similarity import EventSimilarityModel
from app.models.item import ItemModel
from app.models.organization import OrganizationModel
from app.models.registration import RegistrationModel
from app.models.vendor import VendorModel
from app.models.volunteer import VolunteerModel
from app.services.scheduler import scheduler_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create geospatial indexes on startup
    event_model = EventModel.get_instance()
    org_model = OrganizationModel.get_instance()
    event_similarity_model = EventSimilarityModel.get_instance()
    item_model = ItemModel.get_instance()
    registration_model = RegistrationModel.get_instance()
    vendor_model = VendorModel.get_instance()
    volunteer_model = VolunteerModel.get_instance()
    await event_model.create_indexes()
    await org_model.create_indexes()
    await event_similarity_model.create_indexes()
    await item_model.create_indexes()
    await registration_model.create_indexes()
    await vendor_model.create_indexes()
    await volunteer_model.create_indexes()

    # Initialize cache
    redis_backend = RedisBackend(Redis.from_url(settings.REDIS_URL))

    # Initialize FastAPICache
    FastAPICache.init(
        redis_backend,
    )

    # Initialize and start scheduler
    scheduler_service.start()
    yield
    # Shutdown scheduler
    scheduler_service.shutdown()


app = FastAPI(lifespan=lifespan, debug=True)


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


# CORS configuration
origins = [
    "http://localhost",
    "http://192.168.1.34:8000",
    "http://localhost:8000",
    "http://localhost:3000",  # Add your frontend URL here
]

app.add_middleware(NoCacheMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="", tags=["health"])

app.include_router(geocoding.router, prefix="/geocoding", tags=["geocoding"])

app.include_router(user.router, prefix="/user", tags=["user"])

app.include_router(admin.router, prefix="/admin", tags=["admin"])

app.include_router(device_token.router, prefix="/device-token", tags=["device-token"])

app.include_router(item.router, prefix="/item", tags=["item"])

app.include_router(vendor.router, prefix="/vendor", tags=["vendor"])

app.include_router(organization.router, prefix="/organization", tags=["organization"])

app.include_router(event.router, prefix="/event", tags=["event"])

app.include_router(volunteer.router, prefix="/volunteer", tags=["volunteer"])

app.include_router(achievement.router, prefix="/achievement", tags=["achievement"])

app.include_router(
    volunteer_achievement.router, prefix="/volunteer-achievement", tags=["volunteer-achievement"]
)

app.include_router(registration.router, prefix="/registration", tags=["registration"])

app.include_router(order.router, prefix="/order", tags=["order"])

app.include_router(recommendation.router, prefix="/recommendation", tags=["recommendation"])
