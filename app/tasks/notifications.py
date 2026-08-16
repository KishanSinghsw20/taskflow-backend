from datetime import datetime, timezone
import logging
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.notification import Notification
from app.models.project import Project
from app.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.notifications.send_task_reassignment_notification")
def send_task_reassignment_notification(task_id: int, new_assignee_id: int, task_title: str, db=None):
    """Background task to create a notification record when a task is reassigned."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    try:
        notification = Notification(
            user_id=new_assignee_id,
            task_id=task_id,
            type="reassignment",
            message=f"You have been assigned to task '{task_title}' (ID: {task_id}).",
        )
        db.add(notification)
        db.commit()
        logger.info(f"Reassignment notification sent for task {task_id} to user {new_assignee_id}")
    finally:
        if should_close:
            db.close()


@celery_app.task(name="app.tasks.notifications.check_overdue_tasks")
def check_overdue_tasks(db=None):
    """Periodic Celery Beat background task to identify overdue tasks and trigger notifications without duplication."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    try:
        now = datetime.now(timezone.utc)
        overdue_tasks = (
            db.query(Task)
            .filter(Task.due_date < now, Task.status != TaskStatus.DONE)
            .all()
        )

        for task in overdue_tasks:
            project = db.query(Project).filter(Project.id == task.project_id).first()
            target_user_id = task.assignee_id if task.assignee_id else (project.owner_id if project else None)

            if not target_user_id:
                continue

            existing = (
                db.query(Notification)
                .filter(
                    Notification.user_id == target_user_id,
                    Notification.task_id == task.id,
                    Notification.type == "overdue",
                    Notification.is_read.is_(False),
                )
                .first()
            )

            if not existing:
                notification = Notification(
                    user_id=target_user_id,
                    task_id=task.id,
                    type="overdue",
                    message=f"Task '{task.title}' (ID: {task.id}) is past its due date ({task.due_date.isoformat()}).",
                )
                db.add(notification)

        db.commit()
    finally:
        if should_close:
            db.close()

