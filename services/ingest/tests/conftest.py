import pytest
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.config import get_settings
from src.models.indicator import Indicator, Tenant


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture
async def db(settings):
    client = AsyncIOMotorClient(settings.mongo_url)
    database = client["nightjar_test"]
    await init_beanie(database=database, document_models=[Indicator, Tenant])
    yield database
    await client.drop_database("nightjar_test")
    client.close()
