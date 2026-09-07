from datetime import UTC, datetime, timedelta

from src.models.indicator import Indicator, IndicatorType
from src.repositories.indicator_repository import IndicatorRepository

BASE = datetime(2026, 8, 1, tzinfo=UTC)


async def _seed(count: int, tie_groups: int = 4):
    for index in range(count):
        await Indicator(
            tenant_id="acme",
            value=f"198.51.100.{index}",
            indicator_type=IndicatorType.IPV4,
            first_seen=BASE + timedelta(hours=6 * (index % tie_groups)),
        ).insert()


async def test_walk_returns_every_row_exactly_once(db):
    await _seed(40)
    repository = IndicatorRepository()

    seen: set[str] = set()
    offset = 0
    while True:
        items, total = await repository.list_indicators(tenant_id="acme", limit=10, offset=offset)
        if not items:
            break
        seen.update(str(item.id) for item in items)
        offset += 10

    assert total == 40
    assert len(seen) == 40


async def test_total_is_independent_of_the_page(db):
    await _seed(40)
    repository = IndicatorRepository()

    _, first = await repository.list_indicators(tenant_id="acme", limit=10, offset=0)
    _, last = await repository.list_indicators(tenant_id="acme", limit=10, offset=30)

    assert first == last == 40
