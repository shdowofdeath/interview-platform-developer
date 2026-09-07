from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from src.api import assets, feeds, health, indicators, ingest
from src.config import get_settings
from src.db import close_db, init_db
from src.observability.logging import configure_logging
from src.observability.tracing import configure_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging()
    configure_tracing()
    await init_db()
    logger.bind(environment=settings.environment).info("nightjar-ingest api started")
    yield
    await close_db()


app = FastAPI(
    title="Nightjar Ingest",
    version="0.4.2",
    description="Threat-intelligence ingestion and enrichment",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(indicators.router)
app.include_router(feeds.router)
app.include_router(ingest.router)
app.include_router(assets.router)

FastAPIInstrumentor.instrument_app(app)
