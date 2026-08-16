from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.metrics import increment_request_count, router as metrics_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.projects import router as projects_router
from app.api.v1.tasks import router as tasks_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="TaskFlow Backend Take-Home Assignment API",
    version="0.1.0",
)


@app.middleware("http")
def count_requests(request: Request, call_next):
    increment_request_count()
    return call_next(request)


app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(notifications_router)
app.include_router(health_router)
app.include_router(metrics_router)

# Mount static directory if present
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
@app.get("/dashboard")
def dashboard():
    """Serve the interactive web dashboard."""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}



