from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Schema for user login credentials request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for JWT authentication response token."""

    access_token: str
    token_type: str = "bearer"
