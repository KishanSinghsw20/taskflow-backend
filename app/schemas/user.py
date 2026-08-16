from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


class UserCreate(BaseModel):
    """Schema for user signup request."""

    email: EmailStr
    password: str
    name: str


class UserResponse(BaseModel):
    """Schema for user responses without sensitive fields."""

    id: int
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
