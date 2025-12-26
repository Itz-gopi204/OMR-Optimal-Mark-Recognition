from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from beanie import init_beanie
from typing import Optional
import logging

from .settings import settings

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database connection manager."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls) -> None:
        """Connect to MongoDB."""
        try:
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000,
            )
            cls.db = cls.client[settings.MONGODB_DATABASE]

            # Verify connection
            await cls.client.admin.command("ping")
            logger.info(f"Connected to MongoDB: {settings.MONGODB_DATABASE}")

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def disconnect(cls) -> None:
        """Disconnect from MongoDB."""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")

    @classmethod
    async def init_beanie(cls, document_models: list) -> None:
        """Initialize Beanie ODM with document models."""
        if cls.db is None:
            await cls.connect()

        await init_beanie(
            database=cls.db,
            document_models=document_models
        )
        logger.info("Beanie ODM initialized")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if cls.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls.db

    @classmethod
    def get_collection(cls, collection_name: str):
        """Get a specific collection."""
        return cls.get_db()[collection_name]


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    return Database.get_db()
