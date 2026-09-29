from fastapi import FastAPI

from app.api.routes import router
from app.database.db import Base, engine
from app.models.aws_account import AWSAccount  # noqa: F401
from app.models.infrastructure_event import InfrastructureEvent  # noqa: F401
from app.models.organization import Organization  # noqa: F401

app = FastAPI(title="AI Infrastructure Memory")

Base.metadata.create_all(bind=engine)
app.include_router(router)


@app.get("/")
def root():
    return {"message": "AI Infrastructure Memory API", "status": "ok"}
