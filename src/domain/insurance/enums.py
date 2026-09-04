from enum import StrEnum


class PolicyType(StrEnum):
    HOME = "HOME"
    AUTO = "AUTO"


class PolicyStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class NotificationPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
