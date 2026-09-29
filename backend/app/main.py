import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings

from app.api.routes import router
from app.database.db import engine
from app.models.aws_account import AWSAccount  # noqa: F401
from app.models.infrastructure_event import InfrastructureEvent  # noqa: F401
from app.models.infrastructure_incident import InfrastructureIncident  # noqa: F401
from app.models.infrastructure_fix import InfrastructureFix  # noqa: F401
from app.models.infrastructure_metric import InfrastructureMetric  # noqa: F401
from app.models.incident_knowledge_edge import IncidentKnowledgeEdge  # noqa: F401
from app.models.infrastructure_graph import InfrastructureRelationship, InfrastructureResource  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.organization_membership import OrganizationMembership  # noqa: F401
from app.models.user_session import UserSession  # noqa: F401
from app.models.password_reset_token import PasswordResetToken  # noqa: F401
from app.models.auth_audit_log import AuthAuditLog  # noqa: F401
from app.models.email_verification_token import EmailVerificationToken  # noqa: F401
from app.services.collector import cloudtrail_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    worker = asyncio.create_task(cloudtrail_worker(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        await worker


settings = get_settings()
allowed_origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]

app = FastAPI(title="AI Infrastructure Memory", lifespan=lifespan)


@app.get("/health/live")
def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": "unavailable"})

    return {"status": "ready", "database": "ok"}


@app.middleware("http")
async def session_origin_protection(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.cookies.get(settings.auth_cookie_name):
        origin = request.headers.get("origin")
        if origin and origin not in allowed_origins:
            return JSONResponse(status_code=403, content={"detail": "Cross-origin session request blocked"})
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/")
def root():
    return {"message": "AI Infrastructure Memory API", "status": "ok"}
