from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    """Schema for creating a new task within a project."""

    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    assignee_id: int | None = None
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""

    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    assignee_id: int | None = None
    due_date: datetime | None = None


class TaskResponse(BaseModel):
    """Schema for task response."""

    id: int
    project_id: int
    title: str
    description: str | None = None
    status: TaskStatus
    assignee_id: int | None = None
    due_date: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedTasksResponse(BaseModel):
    """Schema for paginated task list response."""

    items: list[TaskResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
