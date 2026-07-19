from typing import Any

from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.entities import get_entities

from backend.app.models.incident import Incident
from backend.app.models.investigation import (
    AffectedAsset,
    InvestigationResult,
)


class InvestigationService:
    """
    Investigates DataPulse AI incidents using DataHub.

    Responsibilities:
    - Trace upstream lineage.
    - Trace downstream blast radius.
    - Retrieve detailed metadata for affected assets.
    - Identify dashboards, datasets, pipelines, owners, and domains.
    """

    def __init__(self, client: DataHubClient):
        self.client = client

    @staticmethod
    def _normalize_lineage_asset(asset: Any) -> AffectedAsset:
        return AffectedAsset(
            urn=str(getattr(asset, "urn", "unknown")),
            name=str(getattr(asset, "name", "Unknown") or "Unknown"),
            asset_type=str(getattr(asset, "type", "UNKNOWN")),
            direction=str(getattr(asset, "direction", "unknown")),
            hops=int(getattr(asset, "hops", 0)),
            platform=str(
                getattr(asset, "platform", None) or "unknown"
            ),
        )

    @staticmethod
    def _extract_description(entity: dict) -> str | None:
        editable = entity.get("editableProperties") or {}
        properties = entity.get("properties") or {}

        return (
            editable.get("description")
            or properties.get("description")
            or entity.get("description")
        )

    @staticmethod
    def _extract_domain(entity: dict) -> str | None:
        domain = entity.get("domain") or {}
        domain_entity = domain.get("domain") or {}
        properties = domain_entity.get("properties") or {}

        return properties.get("name")

    @staticmethod
    def _extract_platform(entity: dict) -> str | None:
        platform = entity.get("platform") or {}

        if isinstance(platform, dict):
            return (
                platform.get("name")
                or (platform.get("properties") or {}).get("displayName")
            )

        return None

    @staticmethod
    def _extract_owners(entity: dict) -> list[str]:
        owner_names: list[str] = []

        ownership = entity.get("ownership") or {}

        for ownership_entry in ownership.get("owners", []):
            owner = ownership_entry.get("owner") or {}

            editable = owner.get("editableProperties") or {}
            properties = owner.get("properties") or {}

            owner_name = (
                editable.get("displayName")
                or properties.get("displayName")
                or properties.get("email")
                or owner.get("name")
                or owner.get("urn")
            )

            if owner_name and owner_name not in owner_names:
                owner_names.append(str(owner_name))

        return owner_names

    @staticmethod
    def _extract_name(entity: dict) -> str | None:
        properties = entity.get("properties") or {}

        return (
            entity.get("name")
            or properties.get("name")
            or entity.get("title")
        )

    def _get_entity_details(
        self,
        urns: list[str],
    ) -> dict[str, dict]:
        """
        Retrieve DataHub metadata in batches.

        get_entities supports multiple URNs in one request, which is
        more efficient than requesting each affected asset separately.
        """

        if not urns:
            return {}

        details_by_urn: dict[str, dict] = {}

        batch_size = 10

        with DataHubContext(self.client):
            for start in range(0, len(urns), batch_size):
                batch = urns[start : start + batch_size]

                results = get_entities(
                    urns=batch,
                )

                for entity in results:
                    urn = entity.get("urn")

                    if urn and "error" not in entity:
                        details_by_urn[urn] = entity

        return details_by_urn

    def _enrich_assets(
        self,
        assets: list[AffectedAsset],
    ) -> list[AffectedAsset]:

        urns = [
            asset.urn
            for asset in assets
            if asset.urn != "unknown"
        ]

        entity_details = self._get_entity_details(urns)

        for asset in assets:
            details = entity_details.get(asset.urn)

            if not details:
                continue

            name = self._extract_name(details)
            platform = self._extract_platform(details)

            if name:
                asset.name = name

            if platform:
                asset.platform = platform

            asset.owner_names = self._extract_owners(details)
            asset.domain_name = self._extract_domain(details)
            asset.description = self._extract_description(details)

        return assets

    @staticmethod
    def _normalize_type(asset_type: str) -> str:
        return asset_type.upper().replace("ENTITYTYPE.", "")

    @classmethod
    def _build_business_summary(
        cls,
        assets: list[AffectedAsset],
    ) -> dict:

        dataset_count = 0
        dashboard_count = 0
        pipeline_count = 0

        owners: set[str] = set()
        domains: set[str] = set()

        for asset in assets:
            asset_type = cls._normalize_type(asset.asset_type)

            if "DATASET" in asset_type:
                dataset_count += 1

            elif "DASHBOARD" in asset_type or "CHART" in asset_type:
                dashboard_count += 1

            elif (
                "DATAFLOW" in asset_type
                or "DATAJOB" in asset_type
                or "PIPELINE" in asset_type
            ):
                pipeline_count += 1

            owners.update(asset.owner_names)

            if asset.domain_name:
                domains.add(asset.domain_name)

        return {
            "datasets": dataset_count,
            "dashboards": dashboard_count,
            "pipelines": pipeline_count,
            "owners": sorted(owners),
            "domains": sorted(domains),
        }

    def investigate(
        self,
        incident: Incident,
        max_hops: int = 3,
    ) -> InvestigationResult:

        incident.mark_investigating()

        upstream_results = self.client.lineage.get_lineage(
            source_urn=incident.asset_urn,
            direction="upstream",
            max_hops=max_hops,
        )

        downstream_results = self.client.lineage.get_lineage(
            source_urn=incident.asset_urn,
            direction="downstream",
            max_hops=max_hops,
        )

        upstream_assets = [
            self._normalize_lineage_asset(asset)
            for asset in upstream_results
        ]

        downstream_assets = [
            self._normalize_lineage_asset(asset)
            for asset in downstream_results
        ]

        upstream_assets = self._enrich_assets(
            upstream_assets
        )

        downstream_assets = self._enrich_assets(
            downstream_assets
        )

        business_summary = self._build_business_summary(
            downstream_assets
        )

        return InvestigationResult(
            incident_id=incident.incident_id,
            source_asset_urn=incident.asset_urn,

            upstream_assets=upstream_assets,
            downstream_assets=downstream_assets,

            total_upstream=len(upstream_assets),
            total_downstream=len(downstream_assets),

            total_affected_assets=(
                len(upstream_assets)
                + len(downstream_assets)
            ),

            affected_datasets=business_summary["datasets"],
            affected_dashboards=business_summary["dashboards"],
            affected_pipelines=business_summary["pipelines"],

            affected_owner_names=business_summary["owners"],
            affected_domains=business_summary["domains"],
        )