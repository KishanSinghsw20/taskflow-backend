from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.redis import redis_client
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", status_code=status.HTTP_200_OK)
def health_check(response: Response, db: Session = Depends(get_db)):
    """Health check endpoint verifying PostgreSQL and Redis connectivity."""
    db_status = "disconnected"
    redis_status = "disconnected"
    is_healthy = True

    # 1. Verify PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        is_healthy = False

    # 2. Verify Redis
    try:
        if redis_client.ping():
            redis_status = "connected"
    except Exception:
        is_healthy = False

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "database": db_status,
            "redis": redis_status,
        }

    return {
        "status": "healthy",
        "database": db_status,
        "redis": redis_status,
    }
