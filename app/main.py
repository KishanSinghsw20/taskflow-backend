from fastapi import FastAPI

app = FastAPI(
    title="TaskFlow API",
    description="TaskFlow Backend Take-Home Assignment API",
    version="0.1.0",
)


@app.get("/")
def root():
    """Root endpoint returning basic service status."""
    return {"message": "Welcome to TaskFlow API"}
