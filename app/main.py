from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="TaskFlow Backend Take-Home Assignment API",
    version="0.1.0",
)

app.include_router(auth_router)



@app.get("/")
def root():
    """Root endpoint returning basic service status."""
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

