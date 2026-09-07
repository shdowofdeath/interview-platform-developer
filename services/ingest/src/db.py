from beanie import init_beanie
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient

from src.config import get_settings
from src.models.indicator import Indicator, Tenant

_client: AsyncIOMotorClient | None = None


async def init_db() -> AsyncIOMotorClient:
    global _client
    settings = get_settings()

    _client = AsyncIOMotorClient(settings.mongo_url, tz_aware=True)
    await init_beanie(database=_client[settings.mongo_database], document_models=[Indicator, Tenant])
    logger.bind(database=settings.mongo_database).info("mongo connected")
    return _client


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("database not initialised")
    return _client
