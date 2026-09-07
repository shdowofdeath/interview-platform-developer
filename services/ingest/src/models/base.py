from datetime import UTC, datetime

from beanie import Document
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class DocumentMetadata(BaseModel):
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BaseDocument(Document):
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)

    async def soft_delete(self) -> None:
        self.metadata.is_deleted = True
        self.metadata.deleted_at = utc_now()
        self.metadata.updated_at = utc_now()
        await self.save()


class BaseTenantDocument(BaseDocument):
    tenant_id: str
