import logging
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis client instance
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis():
    """Dependency or helper to access redis client."""
    return redis_client


def build_tasks_cache_key(
    user_id: int,
    status: str | None,
    assignee_id: int | None,
    due_from: str | None,
    due_to: str | None,
    page: int,
    page_size: int,
) -> str:
    """Build a deterministic Redis cache key isolated by user ID and query parameters."""
    return f"tasks:user:{user_id}:status:{status}:assignee:{assignee_id}:due_from:{due_from}:due_to:{due_to}:page:{page}:page_size:{page_size}"


def invalidate_user_tasks_cache(user_id: int) -> None:
    """Invalidate all task list cache entries for a specific user."""
    try:
        pattern = f"tasks:user:{user_id}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    except Exception as exc:
        logger.warning(f"Failed to invalidate Redis cache for user {user_id}: {exc}")
