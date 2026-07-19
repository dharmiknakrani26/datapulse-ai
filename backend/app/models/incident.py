from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class IncidentType(str, Enum):
    FRESHNESS = "freshness"
    DATA_QUALITY = "data_quality"
    SCHEMA_CHANGE = "schema_change"
    PIPELINE_FAILURE = "pipeline_failure"
    MANUAL = "manual"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


@dataclass
class Incident:
    title: str
    asset_urn: str
    incident_type: IncidentType
    description: str

    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.OPEN

    incident_id: str = field(
        default_factory=lambda: f"DP-{uuid.uuid4().hex[:8].upper()}"
    )

    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    resolved_at: Optional[str] = None

    def mark_investigating(self) -> None:
        self.status = IncidentStatus.INVESTIGATING

    def mark_resolved(self) -> None:
        self.status = IncidentStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)