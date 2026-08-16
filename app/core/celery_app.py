from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "taskflow_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.DEBUG,
    task_eager_propagates=True,
    beat_schedule={
        "check-overdue-tasks-every-5-minutes": {
            "task": "app.tasks.notifications.check_overdue_tasks",
            "schedule": 300.0,
        },
    },
)


celery_app.autodiscover_tasks(["app.tasks"])
