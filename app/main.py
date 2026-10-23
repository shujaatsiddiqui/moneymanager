"""Money Manager API - Main application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import get_api_router
from .database import Base, SessionLocal, engine
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - runs on startup and shutdown."""
    # Startup: Create tables and seed data
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Money Manager API",
    description="Personal finance management API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routes
app.include_router(get_api_router())
