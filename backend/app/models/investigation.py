from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class AffectedAsset:
    urn: str
    name: str
    asset_type: str
    direction: str
    hops: int

    platform: str = "unknown"
    owner_names: list[str] = field(default_factory=list)
    domain_name: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InvestigationResult:
    incident_id: str
    source_asset_urn: str

    upstream_assets: list[AffectedAsset] = field(default_factory=list)
    downstream_assets: list[AffectedAsset] = field(default_factory=list)

    total_upstream: int = 0
    total_downstream: int = 0
    total_affected_assets: int = 0

    affected_datasets: int = 0
    affected_dashboards: int = 0
    affected_pipelines: int = 0

    affected_owner_names: list[str] = field(default_factory=list)
    affected_domains: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)