from src.models.indicator import SourceConfidence
from src.services.confidence import ALERT_THRESHOLD, aggregate, severity_for, should_alert


def _sources(*values: int) -> list[SourceConfidence]:
    return [SourceConfidence(source=f"src-{i}", confidence=v) for i, v in enumerate(values)]


def test_empty_sources_score_zero():
    assert aggregate([]) == 0


def test_single_source_passes_through():
    assert aggregate(_sources(82)) == 82


def test_aggregate_is_the_mean_of_all_sources():
    assert aggregate(_sources(95, 10, 12)) == 39


def test_noisy_source_does_not_dominate():
    """NJ-2841: a single high-scoring source must not drive the aggregate to critical."""
    score = aggregate(_sources(95, 10, 12))
    assert severity_for(score) == "low"
    assert not should_alert(score)


def test_severity_bands():
    assert severity_for(95) == "critical"
    assert severity_for(70) == "high"
    assert severity_for(40) == "medium"
    assert severity_for(0) == "low"


def test_alert_threshold_is_inclusive():
    assert should_alert(ALERT_THRESHOLD)
    assert not should_alert(ALERT_THRESHOLD - 1)
