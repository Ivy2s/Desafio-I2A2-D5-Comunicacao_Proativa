from enum import StrEnum


class EventType(StrEnum):
    HEAVY_RAIN = "HEAVY_RAIN"
    HAIL = "HAIL"
    STRONG_WIND = "STRONG_WIND"


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class EvidenceType(StrEnum):
    ALERT = "ALERT"
    OBSERVATION = "OBSERVATION"
