from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ai, bookings, health, itineraries, service_requests, users
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="MoovAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(users.router)
app.include_router(itineraries.router)
app.include_router(service_requests.router)
app.include_router(bookings.router)
app.include_router(ai.router)
