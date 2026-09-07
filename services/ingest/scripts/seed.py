import asyncio
import hashlib
import json
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db import close_db, init_db
from src.models.base import DocumentMetadata
from src.models.indicator import Indicator, IndicatorType, SourceConfidence, Tenant

SEED = 20260907
BASE = datetime(2026, 8, 1, 0, 0, 0, tzinfo=UTC)

TIE_GROUPS = 28
ACME_COUNT = 2600
GLOBEX_COUNT = 1500

MOCK_UPSTREAM = "http://localhost:9401"

TENANTS = [
    {
        "tenant_id": "acme",
        "name": "Acme Manufacturing",
        "feed_urls": [f"{MOCK_UPSTREAM}/feeds/osint-bundle.json"],
    },
    {
        "tenant_id": "globex",
        "name": "Globex Logistics",
        "feed_urls": [f"{MOCK_UPSTREAM}/feeds/partner-bundle.json"],
    },
]

CURATED_ACME = [
    ("indicator--0b7e2d41-5a63-4c98-8f12-2d6a9e4b7c05", "198.51.100.7", IndicatorType.IPV4, 82, ["command-and-control"]),
    ("indicator--1c8f3e52-6b74-4da9-9023-3e7b0f5c8d16", "198.51.100[.]7", IndicatorType.UNKNOWN, 80, ["malicious-activity"]),
    ("indicator--2d904f63-7c85-4eba-a134-4f8c106d9e27", "198.51.100.7/32", IndicatorType.UNKNOWN, 78, ["malicious-activity"]),
    ("indicator--3ea15074-8d96-4fcb-b245-508d217eaf38", "198.51.100.0/24", IndicatorType.UNKNOWN, 64, ["attribution"]),
    (
        "indicator--4fb26185-9ea7-40dc-c356-619e328fb049",
        "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
        IndicatorType.SHA256,
        91,
        ["malicious-activity"],
    ),
    (
        "indicator--50c37296-afb8-41ed-d467-720f439ac15a",
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        IndicatorType.SHA256,
        88,
        ["malicious-activity"],
    ),
    (
        "indicator--61d483a7-b0c9-42fe-e578-8310540bd26b",
        "hxxp://cdn-update.nightjar-lab[.]test/pkg/loader.bin",
        IndicatorType.UNKNOWN,
        73,
        ["malicious-activity"],
    ),
    (
        "indicator--72e594b8-c1da-430f-f689-9421651ce37c",
        "zzzzGGGG11114444zzzzGGGG11114444zzzzGGGG11114444zzzzGGGG11114444",
        IndicatorType.SHA256,
        40,
        ["anomalous-activity"],
    ),
    (
        "indicator--83f6a5c9-d2eb-4410-0790-a532762df48d",
        "Login-Portal.Nightjar-Lab.TEST",
        IndicatorType.DOMAIN,
        69,
        ["phishing"],
    ),
    (
        "indicator--94a7b6da-e3fc-4521-18a1-b643873ea59e",
        "login-portal.nightjar-lab.test",
        IndicatorType.DOMAIN,
        71,
        ["phishing"],
    ),
]

SOURCE_NAMES = ["passive-dns", "sinkhole", "honeypot", "vendor-feed"]
SEVERITIES = ["low", "medium", "high", "critical"]
LABEL_POOL = [
    "malicious-activity",
    "command-and-control",
    "phishing",
    "reconnaissance",
    "attribution",
    "anomalous-activity",
]


def _severity_for(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _sources(rng: random.Random, target: int) -> list[SourceConfidence]:
    chosen = rng.sample(SOURCE_NAMES, rng.randint(1, 3))
    return [
        SourceConfidence(
            source=name,
            confidence=max(0, min(100, target + rng.randint(-15, 15))),
            observed_at=BASE + timedelta(hours=rng.randint(0, 700)),
        )
        for name in chosen
    ]


def _raw_upstream(rng: random.Random, value: str, first_seen: datetime, sources: list[SourceConfidence]) -> dict:
    return {
        "vendor": "reputation-vendor",
        "vendor_response_version": "2.1.0",
        "indicator": value,
        "first_reported": first_seen.isoformat(),
        "sources": {source.source: source.confidence for source in sources},
        "source_detail": [
            {
                "source": source.source,
                "confidence": source.confidence,
                "observed_at": source.observed_at.isoformat(),
                "collector": f"collector-{rng.randint(1, 40):02d}.{source.source}.vendor.test",
                "sample_ids": [hashlib.sha256(f"{value}{source.source}{n}".encode()).hexdigest() for n in range(6)],
                "campaign_hints": [f"campaign-{rng.randint(1000, 9999)}" for _ in range(4)],
            }
            for source in sources
        ],
        "passive_dns": [
            {
                "rrname": f"{hashlib.sha256(f'{value}{n}'.encode()).hexdigest()[:12]}.nightjar-lab.test",
                "rrtype": rng.choice(["A", "AAAA", "CNAME"]),
                "rdata": f"198.18.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
                "time_first": (first_seen - timedelta(days=rng.randint(1, 400))).isoformat(),
                "time_last": first_seen.isoformat(),
                "count": rng.randint(1, 5000),
            }
            for n in range(rng.randint(6, 12))
        ],
        "whois": {
            "registrar": rng.choice(["Example Registrar LLC", "Test Domains Inc", "Placeholder Registry"]),
            "created": (first_seen - timedelta(days=rng.randint(30, 3000))).isoformat(),
            "nameservers": [f"ns{n}.nightjar-lab.test" for n in range(1, 5)],
            "raw": "Registrar WHOIS response retained verbatim for audit. " * 12,
        },
        "notes": "verbatim upstream payload retained for audit",
    }


def _value(rng: random.Random, index: int) -> tuple[str, IndicatorType]:
    kind = index % 5
    if kind == 0:
        return f"203.0.113.{rng.randint(1, 254)}", IndicatorType.IPV4
    if kind == 1:
        return f"198.18.{rng.randint(0, 255)}.{rng.randint(1, 254)}", IndicatorType.IPV4
    if kind == 2:
        host = hashlib.sha256(f"host-{index}-{SEED}".encode()).hexdigest()[:10]
        return f"{host}.nightjar-lab.test", IndicatorType.DOMAIN
    if kind == 3:
        return hashlib.sha256(f"file-{index}-{SEED}".encode()).hexdigest(), IndicatorType.SHA256
    return hashlib.md5(f"file-{index}-{SEED}".encode()).hexdigest(), IndicatorType.MD5


def _build(
    rng: random.Random,
    tenant_id: str,
    count: int,
    null_enriched_every: int,
    soft_deleted_every: int,
) -> list[Indicator]:
    documents: list[Indicator] = []

    for index in range(count):
        value, indicator_type = _value(rng, index)
        target = rng.randint(5, 98)
        sources = _sources(rng, target)
        score = round(sum(source.confidence for source in sources) / len(sources))

        first_seen = BASE + timedelta(hours=6 * (index % TIE_GROUPS))
        last_seen = first_seen + timedelta(hours=rng.randint(1, 48))

        if index % null_enriched_every == 0:
            last_enriched_at = None
        else:
            last_enriched_at = first_seen + timedelta(minutes=rng.randint(5, 4000))

        metadata = DocumentMetadata(created_at=first_seen, updated_at=last_seen)
        if index % soft_deleted_every == 0 and index > 0:
            metadata.is_deleted = True
            metadata.deleted_at = last_seen + timedelta(days=1)

        documents.append(
            Indicator(
                tenant_id=tenant_id,
                value=value,
                indicator_type=indicator_type,
                stix_id=f"indicator--{hashlib.sha1(f'{tenant_id}-{index}'.encode()).hexdigest()[:8]}"
                f"-0000-4000-8000-{index:012d}",
                source_confidence=sources,
                confidence=score,
                severity=_severity_for(score),
                labels=rng.sample(LABEL_POOL, rng.randint(1, 2)),
                first_seen=first_seen,
                last_seen=last_seen,
                last_enriched_at=last_enriched_at,
                metadata=metadata,
                raw_upstream=_raw_upstream(rng, value, first_seen, sources),
            )
        )

    return documents


def _curated() -> list[Indicator]:
    documents: list[Indicator] = []
    for offset, (stix_id, value, indicator_type, score, labels) in enumerate(CURATED_ACME):
        first_seen = BASE + timedelta(days=13, hours=offset)
        documents.append(
            Indicator(
                tenant_id="acme",
                value=value,
                indicator_type=indicator_type,
                stix_id=stix_id,
                created_by_ref="identity--9a1f4c22-3e8d-4b17-a0c5-71e2d9f83b04",
                source_confidence=[
                    SourceConfidence(source="analyst-review", confidence=score, observed_at=first_seen)
                ],
                confidence=score,
                severity=_severity_for(score),
                labels=labels,
                first_seen=first_seen,
                last_seen=first_seen + timedelta(hours=4),
                last_enriched_at=first_seen + timedelta(hours=1),
                metadata=DocumentMetadata(created_at=first_seen, updated_at=first_seen),
                raw_upstream={"vendor": "analyst-review", "ticket": "NJ-2841"},
            )
        )
    return documents


async def main() -> None:
    rng = random.Random(SEED)

    await init_db()

    await Indicator.get_motor_collection().delete_many({})
    await Tenant.get_motor_collection().delete_many({})

    for spec in TENANTS:
        await Tenant(
            tenant_id=spec["tenant_id"],
            name=spec["name"],
            feed_urls=spec["feed_urls"],
        ).insert()

    acme = _curated() + _build(rng, "acme", ACME_COUNT, null_enriched_every=12, soft_deleted_every=23)
    globex = _build(rng, "globex", GLOBEX_COUNT, null_enriched_every=17, soft_deleted_every=31)

    await Indicator.insert_many(acme)
    await Indicator.insert_many(globex)

    summary = {}
    for tenant_id in ("acme", "globex"):
        collection = Indicator.get_motor_collection()
        summary[tenant_id] = {
            "total": await collection.count_documents({"tenant_id": tenant_id}),
            "live": await collection.count_documents({"tenant_id": tenant_id, "metadata.is_deleted": False}),
            "soft_deleted": await collection.count_documents({"tenant_id": tenant_id, "metadata.is_deleted": True}),
            "never_enriched": await collection.count_documents({"tenant_id": tenant_id, "last_enriched_at": None}),
            "distinct_first_seen": len(await collection.distinct("first_seen", {"tenant_id": tenant_id})),
        }

    logger.info(f"seed complete\n{json.dumps(summary, indent=2)}")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
