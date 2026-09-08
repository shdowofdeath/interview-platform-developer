from datetime import UTC, date, datetime, timedelta

from src.models.indicator import Indicator, IndicatorType
from src.repositories.indicator_repository import IndicatorRepository
from src.services import object_store

CONTRACT = """
Station 1 is not implemented yet.

Create src/activities/export_activities.py defining:

    @dataclass
    class ExportInput:
        tenant_id: str

    @dataclass
    class ExportResult:
        tenant_id: str
        key: str
        records: int

    @activity.defn
    async def export_indicators_activity(payload: ExportInput) -> ExportResult

It must write one JSON object per line to
    <settings.export_prefix>/<tenant_id>/<today>.jsonl
in the bucket named by settings.export_bucket.

src/services/object_store.py already has put_jsonl() for the write.
"""

try:
    from src.activities.export_activities import ExportInput, export_indicators_activity
except ImportError:
    ExportInput = None
    export_indicators_activity = None

BASE = datetime(2026, 8, 1, tzinfo=UTC)

LIVE_ACME = 240
DELETED_ACME = 60
LIVE_GLOBEX = 40


async def _seed():
    batch = []

    for index in range(LIVE_ACME + DELETED_ACME):
        indicator = Indicator(
            tenant_id="acme",
            value=f"198.51.100.{index}",
            indicator_type=IndicatorType.IPV4,
            first_seen=BASE + timedelta(hours=6 * (index % 3)),
        )
        if index >= LIVE_ACME:
            indicator.metadata.is_deleted = True
            indicator.metadata.deleted_at = BASE
        batch.append(indicator)

    for index in range(LIVE_GLOBEX):
        batch.append(
            Indicator(
                tenant_id="globex",
                value=f"203.0.113.{index}",
                indicator_type=IndicatorType.IPV4,
                first_seen=BASE,
            )
        )

    await Indicator.insert_many(batch)


async def _export(tenant_id: str):
    if export_indicators_activity is None:
        raise AssertionError(CONTRACT)
    return await export_indicators_activity(ExportInput(tenant_id=tenant_id))


def _expected_key(tenant_id: str) -> str:
    return f"exports/{tenant_id}/{date.today().isoformat()}.jsonl"


async def test_export_writes_the_object(db, settings):
    await _seed()

    result = await _export("acme")

    assert result.key == _expected_key("acme")
    assert object_store.get_jsonl(settings.export_bucket, result.key)


async def test_export_covers_every_live_indicator(db, settings):
    await _seed()

    result = await _export("acme")
    records = object_store.get_jsonl(settings.export_bucket, result.key)

    live = await IndicatorRepository().count_for_tenant("acme")
    assert live == LIVE_ACME
    assert len(records) == live
    assert result.records == live


async def test_export_holds_one_tenant_only(db, settings):
    await _seed()

    result = await _export("acme")
    records = object_store.get_jsonl(settings.export_bucket, result.key)

    assert {record["tenant_id"] for record in records} == {"acme"}


async def test_export_excludes_soft_deleted_indicators(db, settings):
    await _seed()

    result = await _export("acme")
    records = object_store.get_jsonl(settings.export_bucket, result.key)

    assert not [record for record in records if record.get("metadata", {}).get("is_deleted")]
