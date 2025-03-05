from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
import redis
from app.core.config import settings
import sys
import platform
import time
import psutil

health_router = APIRouter()

@health_router.get("/health", tags=["health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Check API health status.
    Verifies database connection, Redis connection, and system health.
    """
    start_time = time.time()
    
    # Check database connection
    try:
        result = await db.execute("SELECT 1")
        db_status = "up" if result else "down"
    except Exception as e:
        db_status = f"down: {str(e)}"
    
    # Check Redis connection
    try:
        r = redis.from_url(settings.REDIS_URL)
        redis_status = "up" if r.ping() else "down"
    except Exception as e:
        redis_status = f"down: {str(e)}"
    
    # System information
    system_info = {
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "python_version": sys.version,
        "platform": platform.platform(),
    }
    
    response_time = time.time() - start_time
    
    return {
        "status": "ok" if db_status == "up" and redis_status == "up" else "degraded",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "database": db_status,
        "redis": redis_status,
        "system_info": system_info,
        "response_time": response_time
    }

@health_router.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {"message": "Welcome to Voice Agent API"}