from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ResolutionEvidence:
    """
    Evidence supplied by the system responsible for detecting
    whether the original incident condition still exists.

    For the current hackathon demo, this can be a simulated
    detector. Later it can be replaced by a real freshness,
    quality, or assertion signal.
    """

    issue_cleared: bool
    signal_source: str
    details: str

    verification_mode: str = "simulated_demo"

    observed_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    incident_id: str

    verified: bool
    previous_status: str
    current_status: str

    issue_cleared: bool
    source_asset_accessible: bool

    verification_mode: str
    signal_source: str

    message: str

    post_resolution_risk_score: int | None = None

    checked_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)