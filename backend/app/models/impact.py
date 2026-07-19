from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ImpactBreakdown:
    incident_severity: int
    blast_radius: int
    business_exposure: int
    operational_complexity: int
    governance_risk: int

    def total(self) -> int:
        return min(
            100,
            self.incident_severity
            + self.blast_radius
            + self.business_exposure
            + self.operational_complexity
            + self.governance_risk,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ImpactScore:
    score: int
    risk_level: str
    breakdown: ImpactBreakdown
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)