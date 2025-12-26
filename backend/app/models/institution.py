from datetime import datetime
from typing import Optional, List
from beanie import Document, Indexed
from pydantic import Field, EmailStr


class SubscriptionPlan:
    """Subscription plan types."""
    TRIAL = "trial"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class InstitutionStatus:
    """Institution status types."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    PENDING = "pending"


class Subscription(Document):
    """Subscription details embedded document."""

    plan: str = Field(default=SubscriptionPlan.TRIAL)
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    max_users: int = Field(default=10)
    max_sheets_per_month: int = Field(default=100)
    features: List[str] = Field(default_factory=list)


class Branding(Document):
    """Institution branding settings."""

    logo: Optional[str] = None  # S3 URL
    primary_color: str = Field(default="#3B82F6")
    secondary_color: str = Field(default="#1E40AF")


class InstitutionSettings(Document):
    """Institution-specific settings."""

    timezone: str = Field(default="UTC")
    date_format: str = Field(default="YYYY-MM-DD")
    default_language: str = Field(default="en")
    branding: Branding = Field(default_factory=Branding)

    # OMR defaults
    passing_percentage: float = Field(default=35.0)
    negative_marking: bool = Field(default=False)
    negative_mark_value: float = Field(default=0.25)


class Address(Document):
    """Address embedded document."""

    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None


class ContactInfo(Document):
    """Contact information embedded document."""

    email: EmailStr
    phone: Optional[str] = None
    address: Address = Field(default_factory=Address)


class Institution(Document):
    """Institution/Organization model - represents a school or university."""

    # Basic info
    name: Indexed(str)
    slug: Indexed(str, unique=True)  # URL-friendly identifier
    code: Indexed(str, unique=True)  # Unique institution code
    type: str = Field(default="school")  # school, university, coaching

    # Subscription
    subscription: Subscription = Field(default_factory=Subscription)

    # Settings
    settings: InstitutionSettings = Field(default_factory=InstitutionSettings)

    # Contact
    contact: ContactInfo

    # Status
    status: str = Field(default=InstitutionStatus.PENDING)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Audit
    created_by: Optional[str] = None  # User ID of creator (super admin)

    class Settings:
        name = "institutions"
        use_state_management = True

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Springfield High School",
                "slug": "springfield-high",
                "code": "SHS001",
                "type": "school",
                "contact": {
                    "email": "admin@springfield.edu",
                    "phone": "+1-555-0123"
                }
            }
        }

    async def save_with_timestamp(self):
        """Save with updated timestamp."""
        self.updated_at = datetime.utcnow()
        return await self.save()

    def is_active(self) -> bool:
        """Check if institution is active."""
        return self.status == InstitutionStatus.ACTIVE

    def is_subscription_valid(self) -> bool:
        """Check if subscription is valid."""
        if self.subscription.end_date is None:
            return True
        return datetime.utcnow() < self.subscription.end_date

    def can_add_users(self, current_count: int) -> bool:
        """Check if more users can be added."""
        return current_count < self.subscription.max_users

    def has_feature(self, feature: str) -> bool:
        """Check if institution has a specific feature."""
        return feature in self.subscription.features
