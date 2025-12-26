from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class AddressCreate(BaseModel):
    """Address for creation."""

    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None


class ContactInfoCreate(BaseModel):
    """Contact info for creation."""

    email: EmailStr
    phone: Optional[str] = None
    address: Optional[AddressCreate] = None


class BrandingCreate(BaseModel):
    """Branding settings."""

    logo: Optional[str] = None
    primary_color: str = Field(default="#3B82F6")
    secondary_color: str = Field(default="#1E40AF")


class SubscriptionCreate(BaseModel):
    """Subscription settings."""

    plan: str = Field(default="trial")
    max_users: int = Field(default=10, ge=1)
    max_sheets_per_month: int = Field(default=100, ge=1)
    features: List[str] = Field(default_factory=list)


class InstitutionSettingsCreate(BaseModel):
    """Institution settings."""

    timezone: str = Field(default="UTC")
    date_format: str = Field(default="YYYY-MM-DD")
    default_language: str = Field(default="en")
    branding: Optional[BrandingCreate] = None
    passing_percentage: float = Field(default=35.0, ge=0, le=100)
    negative_marking: bool = Field(default=False)
    negative_mark_value: float = Field(default=0.25, ge=0)


class InstitutionCreateRequest(BaseModel):
    """Create institution request."""

    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    code: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Z0-9]+$")
    type: str = Field(default="school")
    contact: ContactInfoCreate
    subscription: Optional[SubscriptionCreate] = None
    settings: Optional[InstitutionSettingsCreate] = None

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


class InstitutionUpdateRequest(BaseModel):
    """Update institution request."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    type: Optional[str] = None
    contact: Optional[ContactInfoCreate] = None
    subscription: Optional[SubscriptionCreate] = None
    settings: Optional[InstitutionSettingsCreate] = None
    status: Optional[str] = None


class AddressResponse(BaseModel):
    """Address response."""

    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None


class ContactInfoResponse(BaseModel):
    """Contact info response."""

    email: str
    phone: Optional[str] = None
    address: Optional[AddressResponse] = None


class BrandingResponse(BaseModel):
    """Branding response."""

    logo: Optional[str] = None
    primary_color: str
    secondary_color: str


class SubscriptionResponse(BaseModel):
    """Subscription response."""

    plan: str
    start_date: datetime
    end_date: Optional[datetime] = None
    max_users: int
    max_sheets_per_month: int
    features: List[str]


class InstitutionSettingsResponse(BaseModel):
    """Institution settings response."""

    timezone: str
    date_format: str
    default_language: str
    branding: Optional[BrandingResponse] = None
    passing_percentage: float
    negative_marking: bool
    negative_mark_value: float


class InstitutionResponse(BaseModel):
    """Institution response."""

    id: str
    name: str
    slug: str
    code: str
    type: str
    contact: ContactInfoResponse
    subscription: SubscriptionResponse
    settings: InstitutionSettingsResponse
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InstitutionListResponse(BaseModel):
    """Paginated institution list response."""

    items: List[InstitutionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class InstitutionStatsResponse(BaseModel):
    """Institution statistics."""

    total_users: int
    total_tests: int
    total_sheets_processed: int
    active_users: int
    sheets_this_month: int
