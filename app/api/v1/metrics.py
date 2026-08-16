import time
from fastapi import APIRouter, Response

router = APIRouter(prefix="/metrics", tags=["metrics"])

START_TIME = time.time()
REQUEST_COUNT = 0


def increment_request_count():
    global REQUEST_COUNT
    REQUEST_COUNT += 1


@router.get("", response_class=Response)
def metrics():
    """Metrics endpoint in Prometheus text format."""
    uptime = time.time() - START_TIME
    metrics_data = f"""# HELP http_requests_total Total number of HTTP requests processed.
# TYPE http_requests_total counter
http_requests_total {REQUEST_COUNT}

# HELP app_uptime_seconds Application uptime in seconds.
# TYPE app_uptime_seconds gauge
app_uptime_seconds {uptime:.2f}
"""
    return Response(content=metrics_data, media_type="text/plain")
