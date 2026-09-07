from fastapi import Header

from src.repositories.indicator_repository import IndicatorRepository


async def tenant_from_header(x_tenant_id: str = Header(..., alias="X-Tenant-Id")) -> str:
    return x_tenant_id


def indicator_repository() -> IndicatorRepository:
    return IndicatorRepository()
