from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.search import search

from backend.app.models.commander import IncidentCommanderResult
from backend.app.models.impact import (
    ImpactBreakdown,
    ImpactScore,
)
from backend.app.models.incident import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
)
from backend.app.models.investigation import (
    AffectedAsset,
    InvestigationResult,
)
from backend.app.models.resolution import ResolutionEvidence
from backend.app.services.datahub_writeback_service import (
    DataHubWritebackService,
)
from backend.app.services.impact_service import ImpactService
from backend.app.services.incident_commander_service import (
    IncidentCommanderService,
)
from backend.app.services.incident_memory_service import (
    IncidentMemoryService,
)
from backend.app.services.incident_service import IncidentService
from backend.app.services.investigation_service import (
    InvestigationService,
)
from backend.app.services.lineage_graph_service import (
    LineageGraphService,
)
from backend.app.services.resolution_verification_service import (
    ResolutionVerificationService,
)


class IncidentWorkflowService:
    """
    Main application workflow for DataPulse AI.

    Coordinates:

    Dataset Discovery
    -> Incident Creation
    -> DataHub Investigation
    -> Blast Radius
    -> Impact Score
    -> AI Incident Commander
    -> DataHub Writeback
    -> Incident Memory
    -> Resolution Verification
    """

    def __init__(self) -> None:
        self.client = DataHubClient.from_env()
        self.memory = IncidentMemoryService()

    # =========================================================
    # Asset Discovery
    # =========================================================

    def search_assets(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict]:

        with DataHubContext(self.client):
            results = search(
                query=f"/q {query}",
                filter="entity_type = dataset",
                num_results=limit,
            )

        assets: list[dict] = []

        for result in results.get(
            "searchResults",
            [],
        ):
            entity = result.get(
                "entity",
                {},
            )

            urn = entity.get("urn")

            if not urn:
                continue

            properties = (
                entity.get("properties")
                or {}
            )

            name = (
                entity.get("name")
                or properties.get("name")
                or "Unknown Dataset"
            )

            assets.append(
                {
                    "urn": urn,
                    "name": name,
                }
            )

        return assets

    def find_connected_dataset(
        self,
        query: str = "orders",
        max_hops: int = 3,
    ) -> str:
        """
        Find a dataset with downstream lineage.
        """

        assets = self.search_assets(
            query=query,
            limit=20,
        )

        for asset in assets:
            urn = asset["urn"]

            downstream = (
                self.client.lineage.get_lineage(
                    source_urn=urn,
                    direction="downstream",
                    max_hops=max_hops,
                )
            )

            if downstream:
                return urn

        raise RuntimeError(
            f"No connected dataset found for search query: {query}"
        )

    # =========================================================
    # Incident Creation
    # =========================================================

    @staticmethod
    def _create_incident(
        asset_urn: str,
        incident_type: str,
    ) -> Incident:

        if incident_type == "freshness":
            return (
                IncidentService
                .create_freshness_incident(
                    asset_urn=asset_urn
                )
            )

        if incident_type == "data_quality":
            return (
                IncidentService
                .create_data_quality_incident(
                    asset_urn=asset_urn
                )
            )

        if incident_type == "schema_change":
            return (
                IncidentService
                .create_schema_change_incident(
                    asset_urn=asset_urn
                )
            )

        raise ValueError(
            f"Unsupported incident type: {incident_type}"
        )

    # =========================================================
    # Full Investigation Workflow
    # =========================================================

    def analyze_incident(
        self,
        incident_type: str,
        asset_urn: str | None = None,
        search_query: str = "orders",
        max_hops: int = 3,
    ) -> dict:

        if not asset_urn:
            asset_urn = (
                self.find_connected_dataset(
                    query=search_query,
                    max_hops=max_hops,
                )
            )

        incident = self._create_incident(
            asset_urn=asset_urn,
            incident_type=incident_type,
        )

        investigator = InvestigationService(
            self.client
        )

        investigation = (
            investigator.investigate(
                incident=incident,
                max_hops=max_hops,
            )
        )

        impact = ImpactService.calculate(
            incident=incident,
            investigation=investigation,
        )

        commander_service = (
            IncidentCommanderService()
        )

        commander = (
            commander_service.analyze(
                incident=incident,
                investigation=investigation,
                impact=impact,
            )
        )

        writeback = (
            DataHubWritebackService()
        )

        writeback.write_incident_analysis(
            incident=incident,
            investigation=investigation,
            impact=impact,
            commander=commander,
        )

        self.memory.save_incident(
            incident=incident,
            investigation=investigation,
            impact=impact,
            commander=commander,
        )

        saved_record = (
            self.memory.get_incident(
                incident.incident_id
            )
        )

        if not saved_record:
            raise RuntimeError(
                "Incident completed but could not "
                "be retrieved from incident memory."
            )

        return saved_record

    # =========================================================
    # Incident History
    # =========================================================

    def get_all_incidents(
        self,
    ) -> list[dict]:

        records = (
            self.memory.get_all_incidents()
        )

        return list(
            reversed(records)
        )

    def get_incident(
        self,
        incident_id: str,
    ) -> dict | None:

        return (
            self.memory.get_incident(
                incident_id
            )
        )

    # =========================================================
    # Restore Stored Objects
    # =========================================================

    @staticmethod
    def _restore_incident(
        data: dict,
    ) -> Incident:

        return Incident(
            title=data["title"],
            asset_urn=data["asset_urn"],
            incident_type=IncidentType(
                data["incident_type"]
            ),
            description=data["description"],
            severity=IncidentSeverity(
                data["severity"]
            ),
            status=IncidentStatus(
                data["status"]
            ),
            incident_id=data["incident_id"],
            created_at=data["created_at"],
            resolved_at=data.get(
                "resolved_at"
            ),
        )

    @staticmethod
    def _restore_investigation(
        data: dict,
    ) -> InvestigationResult:

        upstream_assets = [
            AffectedAsset(**asset)
            for asset in data.get(
                "upstream_assets",
                [],
            )
        ]

        downstream_assets = [
            AffectedAsset(**asset)
            for asset in data.get(
                "downstream_assets",
                [],
            )
        ]

        return InvestigationResult(
            incident_id=data["incident_id"],
            source_asset_urn=(
                data["source_asset_urn"]
            ),
            upstream_assets=upstream_assets,
            downstream_assets=downstream_assets,
            total_upstream=data.get(
                "total_upstream",
                0,
            ),
            total_downstream=data.get(
                "total_downstream",
                0,
            ),
            total_affected_assets=data.get(
                "total_affected_assets",
                0,
            ),
            affected_datasets=data.get(
                "affected_datasets",
                0,
            ),
            affected_dashboards=data.get(
                "affected_dashboards",
                0,
            ),
            affected_pipelines=data.get(
                "affected_pipelines",
                0,
            ),
            affected_owner_names=data.get(
                "affected_owner_names",
                [],
            ),
            affected_domains=data.get(
                "affected_domains",
                [],
            ),
        )

    @staticmethod
    def _restore_impact(
        data: dict,
    ) -> ImpactScore:

        breakdown = ImpactBreakdown(
            **data["breakdown"]
        )

        return ImpactScore(
            score=data["score"],
            risk_level=data["risk_level"],
            breakdown=breakdown,
            explanation=data["explanation"],
        )

    @staticmethod
    def _restore_commander(
        data: dict,
    ) -> IncidentCommanderResult:

        return (
            IncidentCommanderResult
            .model_validate(
                data
            )
        )

    # =========================================================
    # Lineage Graph
    # =========================================================

    def get_lineage_graph(
        self,
        incident_id: str,
    ) -> dict:

        record = (
            self.memory.get_incident(
                incident_id
            )
        )

        if not record:
            raise KeyError(
                f"Incident not found: {incident_id}"
            )

        investigation = (
            self._restore_investigation(
                record["investigation"]
            )
        )

        source_asset_urn = (
            record["incident"]["asset_urn"]
        )

        graph_service = (
            LineageGraphService(
                self.client
            )
        )

        return graph_service.build_graph(
            source_asset_urn=source_asset_urn,
            investigation=investigation,
        )

    # =========================================================
    # Resolution Workflow
    # =========================================================

    def resolve_incident(
        self,
        incident_id: str,
        issue_cleared: bool,
        signal_source: str,
        details: str,
        verification_mode: str,
    ) -> dict:

        record = (
            self.memory.get_incident(
                incident_id
            )
        )

        if not record:
            raise KeyError(
                f"Incident not found: {incident_id}"
            )

        if (
            record["incident"].get("status")
            == IncidentStatus.RESOLVED.value
        ):
            return record

        incident = self._restore_incident(
            record["incident"]
        )

        investigation = (
            self._restore_investigation(
                record["investigation"]
            )
        )

        impact = self._restore_impact(
            record["impact"]
        )

        commander = (
            self._restore_commander(
                record[
                    "commander_analysis"
                ]
            )
        )

        evidence = ResolutionEvidence(
            issue_cleared=issue_cleared,
            signal_source=signal_source,
            details=details,
            verification_mode=verification_mode,
        )

        verifier = (
            ResolutionVerificationService(
                self.client
            )
        )

        verification = verifier.verify(
            incident=incident,
            evidence=evidence,
        )

        self.memory.save_incident(
            incident=incident,
            investigation=investigation,
            impact=impact,
            commander=commander,
            verification=verification,
        )

        if verification.verified:

            writeback = (
                DataHubWritebackService()
            )

            writeback.write_incident_analysis(
                incident=incident,
                investigation=investigation,
                impact=impact,
                commander=commander,
            )

        updated_record = (
            self.memory.get_incident(
                incident_id
            )
        )

        if not updated_record:
            raise RuntimeError(
                "Incident resolution completed "
                "but the updated record could not "
                "be loaded."
            )

        return updated_record