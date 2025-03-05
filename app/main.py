from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from typing import Callable
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.api.router import api_router
from app.api.health import health_router
from app.core.config import settings
from app.db.session import engine, init_db

# Configure Sentry if DSN is provided
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.2,
    )

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Voice Agent API",
    description="API for voice agent system handling inbound and outbound calls",
    version="1.0.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request ID middleware
@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next: Callable):
    request_id = request.headers.get("X-Request-ID", None)
    if not request_id:
        request_id = str(int(time.time() * 1000))
        request.headers.__dict__["_headers"]["x-request-id"] = request_id
    
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        logger.exception(f"Request failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )

# Include routers
app.include_router(health_router)
app.include_router(api_router, prefix="/api")

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Voice Agent API")
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Voice Agent API")