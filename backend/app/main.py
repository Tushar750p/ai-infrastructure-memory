from fastapi import FastAPI
from app.api.routes import router as api_router
from app.database.db import engine, Base
from app.models.user import User  # This registers the model

# Create tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Infrastructure Memory API", version="0.1")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "AI Infrastructure Memory API Cluster is Running"}
