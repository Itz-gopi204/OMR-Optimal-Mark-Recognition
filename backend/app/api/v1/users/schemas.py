from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

from app.models.user import UserRole, UserStatus


class UserProfileCreate(BaseModel):
    """User profile for creation."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None
    student_id: Optional[str] = None
    employee_id: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """User profile for updates."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    student_id: Optional[str] = None
    employee_id: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None


class UserCreateRequest(BaseModel):
    """Create user request schema."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    profile: UserProfileCreate
    role: UserRole = Field(default=UserRole.STUDENT)
    department: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "teacher@school.edu",
                "password": "SecurePass123!",
                "profile": {
                    "first_name": "Jane",
                    "last_name": "Smith"
                },
                "role": "teacher",
                "department": "Mathematics"
            }
        }


class UserUpdateRequest(BaseModel):
    """Update user request schema."""

    profile: Optional[UserProfileUpdate] = None
    role: Optional[UserRole] = None
    department: Optional[str] = None
    status: Optional[UserStatus] = None

    class Config:
        json_schema_extra = {
            "example": {
                "profile": {
                    "first_name": "Jane",
                    "phone": "+1-555-0123"
                },
                "department": "Science"
            }
        }


class UserProfileResponse(BaseModel):
    """User profile response."""

    first_name: str
    last_name: str
    avatar: Optional[str] = None
    phone: Optional[str] = None
    student_id: Optional[str] = None
    employee_id: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema."""

    id: str
    email: str
    profile: UserProfileResponse
    role: str
    department: Optional[str] = None
    institution_id: Optional[str] = None
    status: str
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list response."""

    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BulkImportResult(BaseModel):
    """Bulk import result."""

    total: int
    successful: int
    failed: int
    errors: List[dict]


class UserStatsResponse(BaseModel):
    """User statistics response."""

    total_users: int
    active_users: int
    by_role: dict
    recent_signups: int
