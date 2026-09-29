import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.database.db import Base, engine
from app.models.aws_account import AWSAccount  # noqa: F401
from app.models.infrastructure_event import InfrastructureEvent  # noqa: F401
from app.models.infrastructure_graph import InfrastructureRelationship, InfrastructureResource  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.services.collector import cloudtrail_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    stop_event = asyncio.Event()
    worker = asyncio.create_task(cloudtrail_worker(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        await worker


app = FastAPI(title="AI Infrastructure Memory", lifespan=lifespan)
app.include_router(router)


@app.get("/")
def root():
    return {"message": "AI Infrastructure Memory API", "status": "ok"}
