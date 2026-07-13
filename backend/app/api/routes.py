from fastapi import APIRouter
from app.database.db import redis_client, engine

router = APIRouter()

@router.get("/health")
def health_check():
    # Check PostgreSQL status
    try:
        engine.connect()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Check Redis status
    try:
        redis_client.ping()
        redis_status = "connected"
    except Exception:
        redis_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" and redis_status == "connected" else "unhealthy",
        "database": db_status,
        "redis": redis_status,
        "version": "0.1"
    }
