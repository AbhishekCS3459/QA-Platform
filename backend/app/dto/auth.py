"""
Auth DTOs
"""
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72, description="Password must be between 6 and 72 characters (bcrypt limitation)")
    
    @field_validator('password')
    @classmethod
    def validate_password_bytes(cls, v: str) -> str:
        """Validate that password doesn't exceed 72 bytes (bcrypt limitation)"""
        password_bytes = v.encode('utf-8')
        if len(password_bytes) > 72:
            raise ValueError(
                "Password cannot exceed 72 bytes when encoded as UTF-8. "
                "This typically means your password is too long or contains too many multi-byte characters."
            )
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True

