import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from datahub.ingestion.graph.client import (
    DataHubGraph,
    DataHubGraphConfig,
)
from datahub.specific.dataset import DatasetPatchBuilder

from backend.app.models.commander import IncidentCommanderResult
from backend.app.models.impact import ImpactScore
from backend.app.models.incident import Incident
from backend.app.models.investigation import InvestigationResult


load_dotenv()


class DataHubWritebackService:
    """
    Writes DataPulse AI incident intelligence back into DataHub.

    For the hackathon MVP, investigation results are stored as
    custom properties on the source dataset.

    Patch updates are used so existing dataset metadata is not
    replaced or destroyed.
    """

    def __init__(self) -> None:
        server = os.getenv(
            "DATAHUB_GMS_URL",
            "http://localhost:8080",
        ).strip()

        token = os.getenv(
            "DATAHUB_GMS_TOKEN",
            "",
        ).strip()

        if not token:
            raise RuntimeError(
                "DATAHUB_GMS_TOKEN is missing from the .env file."
            )

        self.graph = DataHubGraph(
            DataHubGraphConfig(
                server=server,
                token=token,
            )
        )

    @staticmethod
    def _truncate(
        value: str,
        max_length: int = 500,
    ) -> str:
        """
        Keep custom-property values reasonably small.
        """

        value = str(value).strip()

        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."

    def write_incident_analysis(
        self,
        incident: Incident,
        investigation: InvestigationResult,
        impact: ImpactScore,
        commander: IncidentCommanderResult,
    ) -> None:
        """
        Write DataPulse investigation metadata onto the
        source dataset.
        """

        analysis_timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        patch_builder = DatasetPatchBuilder(
            incident.asset_urn
        )

        patch_builder.add_custom_property(
            "datapulse_incident_id",
            incident.incident_id,
        )

        patch_builder.add_custom_property(
            "datapulse_incident_type",
            incident.incident_type.value,
        )

        patch_builder.add_custom_property(
            "datapulse_incident_status",
            incident.status.value,
        )

        patch_builder.add_custom_property(
            "datapulse_impact_score",
            str(impact.score),
        )

        patch_builder.add_custom_property(
            "datapulse_risk_level",
            impact.risk_level,
        )

        patch_builder.add_custom_property(
            "datapulse_downstream_assets",
            str(investigation.total_downstream),
        )

        patch_builder.add_custom_property(
            "datapulse_affected_dashboards",
            str(investigation.affected_dashboards),
        )

        patch_builder.add_custom_property(
            "datapulse_affected_domains",
            str(
                len(
                    investigation.affected_domains
                )
            ),
        )

        patch_builder.add_custom_property(
            "datapulse_root_cause_confidence",
            str(
                commander.root_cause_confidence
            ),
        )

        patch_builder.add_custom_property(
            "datapulse_root_cause_hypothesis",
            self._truncate(
                commander.root_cause_hypothesis
            ),
        )

        patch_builder.add_custom_property(
            "datapulse_executive_summary",
            self._truncate(
                commander.executive_summary
            ),
        )

        patch_builder.add_custom_property(
            "datapulse_last_analysis",
            analysis_timestamp,
        )

        patch_mcps = patch_builder.build()

        for patch_mcp in patch_mcps:
            self.graph.emit(
                patch_mcp
            )