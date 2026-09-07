from fastapi import APIRouter, Query

from src.services import cpe_matcher

router = APIRouter(prefix="/api/v1", tags=["assets"])


@router.get("/cve/applicable")
async def applicable_cves(cpe: str = Query(...)) -> dict[str, object]:
    cve_ids = cpe_matcher.applicable_cves(cpe)
    return {"cpe": cpe, "cve_ids": cve_ids, "count": len(cve_ids)}


@router.get("/cve/applicable-for")
async def applicable_for_product(
    vendor: str = Query(...),
    product: str = Query(...),
    version: str = Query(...),
) -> dict[str, object]:
    cpe = cpe_matcher.build_cpe_uri(vendor, product, version)
    cve_ids = cpe_matcher.applicable_cves(cpe)
    return {"cpe": cpe, "cve_ids": cve_ids, "count": len(cve_ids)}
