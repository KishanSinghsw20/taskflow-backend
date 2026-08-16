import math
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.projects import get_user_project
from app.core.redis import build_tasks_cache_key, invalidate_user_tasks_cache, redis_client
from app.db.session import get_db
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.task import PaginatedTasksResponse, TaskCreate, TaskResponse, TaskUpdate
from app.tasks.notifications import send_task_reassignment_notification


router = APIRouter(tags=["tasks"])


def get_user_task(task_id: int, db: Session, current_user: User) -> Task:
    """Helper function to retrieve a task ensuring the project belongs to the current user."""
    task = (
        db.query(Task)
        .join(Project, Task.project_id == Project.id)
        .filter(Task.id == task_id, Project.owner_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )
    return task


@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    project_id: int,
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a task inside a project owned by the current authenticated user."""
    get_user_project(project_id, db, current_user)

    if task_in.assignee_id is not None:
        assignee = db.query(User).filter(User.id == task_in.assignee_id).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user does not exist.",
            )

    task = Task(
        project_id=project_id,
        title=task_in.title,
        description=task_in.description,
        status=task_in.status,
        assignee_id=task_in.assignee_id,
        due_date=task_in.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    if task.assignee_id:
        try:
            send_task_reassignment_notification.delay(task.id, task.assignee_id, task.title)
        except Exception:
            # Fallback for sync execution if Celery broker unavailable during tests/dev
            pass

    # Invalidate task list cache for current user
    invalidate_user_tasks_cache(current_user.id)
    return task



@router.get("/tasks", response_model=PaginatedTasksResponse)
def list_tasks(
    status: TaskStatus | None = Query(None, description="Filter by task status"),
    assignee_id: int | None = Query(None, description="Filter by assignee user ID"),
    due_from: datetime | None = Query(None, description="Filter tasks due from datetime"),
    due_to: datetime | None = Query(None, description="Filter tasks due to datetime"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tasks belonging to the current user's projects with Redis caching, filtering, and pagination."""
    due_from_str = due_from.isoformat() if due_from else None
    due_to_str = due_to.isoformat() if due_to else None
    status_str = status.value if status else None

    cache_key = build_tasks_cache_key(
        user_id=current_user.id,
        status=status_str,
        assignee_id=assignee_id,
        due_from=due_from_str,
        due_to=due_to_str,
        page=page,
        page_size=page_size,
    )

    # 1. Attempt cache hit from Redis
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return PaginatedTasksResponse.model_validate_json(cached_data)
    except Exception:
        pass

    # 2. Database query fallback
    query = db.query(Task).join(Project, Task.project_id == Project.id).filter(Project.owner_id == current_user.id)

    if status:
        query = query.filter(Task.status == status)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    if due_from:
        query = query.filter(Task.due_date >= due_from)
    if due_to:
        query = query.filter(Task.due_date <= due_to)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(Task.created_at.desc()).offset(offset).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    response = PaginatedTasksResponse(
        items=[TaskResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )

    # 3. Store result in Redis cache (TTL 5 minutes)
    try:
        redis_client.setex(cache_key, 300, response.model_dump_json())
    except Exception:
        pass

    return response


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details of a task owned by the current authenticated user."""
    return get_user_task(task_id, db, current_user)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update fields of a task owned by the current authenticated user."""
    task = get_user_task(task_id, db, current_user)
    old_assignee_id = task.assignee_id

    if task_in.assignee_id is not None:
        assignee = db.query(User).filter(User.id == task_in.assignee_id).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user does not exist.",
            )

    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.add(task)
    db.commit()
    db.refresh(task)

    # Queue notification if task is reassigned to a new user
    if task.assignee_id and task.assignee_id != old_assignee_id:
        try:
            send_task_reassignment_notification.delay(task.id, task.assignee_id, task.title)
        except Exception:
            pass

    # Invalidate task list cache for current user
    invalidate_user_tasks_cache(current_user.id)
    return task



@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a task owned by the current authenticated user."""
    task = get_user_task(task_id, db, current_user)
    db.delete(task)
    db.commit()

    # Invalidate task list cache for current user
    invalidate_user_tasks_cache(current_user.id)
    return None

