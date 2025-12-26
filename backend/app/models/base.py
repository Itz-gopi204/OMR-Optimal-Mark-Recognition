from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import Field


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BaseDocument(Document, TimestampMixin):
    """Base document class with common fields."""

    class Settings:
        use_state_management = True
        validate_on_save = True

    async def save_with_timestamp(self, *args, **kwargs):
        """Save document with updated timestamp."""
        self.updated_at = datetime.utcnow()
        return await self.save(*args, **kwargs)
