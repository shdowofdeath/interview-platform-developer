from src.models.indicator import SourceConfidence

ALERT_THRESHOLD = 70

SEVERITY_BANDS = [
    (90, "critical"),
    (70, "high"),
    (40, "medium"),
    (0, "low"),
]


def aggregate(sources: list[SourceConfidence]) -> int:
    if not sources:
        return 0
    return round(sum(source.confidence for source in sources) / len(sources))


def severity_for(confidence: int) -> str:
    for floor, label in SEVERITY_BANDS:
        if confidence >= floor:
            return label
    return "unknown"


def should_alert(confidence: int) -> bool:
    return confidence >= ALERT_THRESHOLD
