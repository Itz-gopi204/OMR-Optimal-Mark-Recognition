from datetime import datetime
from typing import Optional, List
from enum import Enum
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field, EmailStr


class UserRole(str, Enum):
    """User role enumeration."""
    SUPER_ADMIN = "super_admin"
    INSTITUTION_ADMIN = "institution_admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"
    SUSPENDED = "suspended"


class UserProfile(Document):
    """User profile embedded document."""

    first_name: str
    last_name: str
    avatar: Optional[str] = None  # S3 URL
    phone: Optional[str] = None
    student_id: Optional[str] = None  # For students
    employee_id: Optional[str] = None  # For staff
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None


class OAuthProvider(Document):
    """OAuth provider details."""

    id: str
    email: EmailStr


class OAuthConnections(Document):
    """OAuth connections embedded document."""

    google: Optional[OAuthProvider] = None
    microsoft: Optional[OAuthProvider] = None


class NotificationPreferences(Document):
    """Notification preferences."""

    email: bool = True
    push: bool = True
    sms: bool = False


class UserPreferences(Document):
    """User preferences embedded document."""

    notifications: NotificationPreferences = Field(default_factory=NotificationPreferences)
    language: str = Field(default="en")
    theme: str = Field(default="light")


class User(Document):
    """User model with multi-tenant support."""

    # Core fields
    email: Indexed(EmailStr, unique=True)
    password_hash: str

    # Institution (null for super admins)
    institution_id: Optional[PydanticObjectId] = None

    # Profile
    profile: UserProfile

    # Role and permissions
    role: UserRole = Field(default=UserRole.STUDENT)
    permissions: List[str] = Field(default_factory=list)  # Additional fine-grained permissions

    # Organization
    department: Optional[str] = None
    classes: List[PydanticObjectId] = Field(default_factory=list)  # For teachers/students

    # Parent-student relationship
    parent_of: List[PydanticObjectId] = Field(default_factory=list)  # For parents

    # OAuth
    oauth: OAuthConnections = Field(default_factory=OAuthConnections)

    # Preferences
    preferences: UserPreferences = Field(default_factory=UserPreferences)

    # Status
    status: UserStatus = Field(default=UserStatus.PENDING_VERIFICATION)

    # Authentication
    last_login_at: Optional[datetime] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    email_verification_token: Optional[str] = None
    email_verified: bool = False

    # Two-factor authentication
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        use_state_management = True
        indexes = [
            "email",
            "institution_id",
            [("institution_id", 1), ("role", 1)],
            [("institution_id", 1), ("profile.student_id", 1)],
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@school.edu",
                "profile": {
                    "first_name": "John",
                    "last_name": "Doe"
                },
                "role": "teacher",
                "department": "Mathematics"
            }
        }

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.profile.first_name} {self.profile.last_name}"

    def is_super_admin(self) -> bool:
        """Check if user is super admin."""
        return self.role == UserRole.SUPER_ADMIN

    def is_institution_admin(self) -> bool:
        """Check if user is institution admin."""
        return self.role == UserRole.INSTITUTION_ADMIN

    def is_teacher(self) -> bool:
        """Check if user is teacher."""
        return self.role == UserRole.TEACHER

    def is_student(self) -> bool:
        """Check if user is student."""
        return self.role == UserRole.STUDENT

    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def can_access_institution(self, institution_id: str) -> bool:
        """Check if user can access a specific institution."""
        if self.is_super_admin():
            return True
        return str(self.institution_id) == institution_id

    async def save_with_timestamp(self):
        """Save with updated timestamp."""
        self.updated_at = datetime.utcnow()
        return await self.save()

    def to_public_dict(self) -> dict:
        """Return public-safe user data (no sensitive fields)."""
        return {
            "id": str(self.id),
            "email": self.email,
            "profile": {
                "first_name": self.profile.first_name,
                "last_name": self.profile.last_name,
                "avatar": self.profile.avatar,
            },
            "role": self.role.value,
            "institution_id": str(self.institution_id) if self.institution_id else None,
            "status": self.status.value,
        }
