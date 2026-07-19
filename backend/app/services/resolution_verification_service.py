from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.entities import get_entities

from backend.app.models.incident import Incident
from backend.app.models.resolution import (
    ResolutionEvidence,
    VerificationResult,
)


class ResolutionVerificationService:
    """
    Verifies whether a DataPulse incident can be resolved.

    Resolution currently requires:

    1. The source asset must still be accessible in DataHub.
    2. The incident detector must explicitly report that the
       original issue has cleared.

    This avoids falsely claiming that lineage alone proves
    an operational problem has been fixed.
    """

    def __init__(
        self,
        client: DataHubClient,
    ) -> None:
        self.client = client

    def _source_asset_is_accessible(
        self,
        asset_urn: str,
    ) -> bool:
        """
        Confirm that the incident source asset still exists
        and can be retrieved from DataHub.
        """

        with DataHubContext(self.client):
            results = get_entities(
                urns=[asset_urn],
            )

        for entity in results:
            urn = entity.get("urn")

            if (
                urn == asset_urn
                and "error" not in entity
            ):
                return True

        return False

    def verify(
        self,
        incident: Incident,
        evidence: ResolutionEvidence,
    ) -> VerificationResult:

        previous_status = incident.status.value

        source_accessible = (
            self._source_asset_is_accessible(
                incident.asset_urn
            )
        )

        # -----------------------------------------------------
        # DataHub source asset cannot be verified
        # -----------------------------------------------------

        if not source_accessible:
            return VerificationResult(
                incident_id=incident.incident_id,
                verified=False,
                previous_status=previous_status,
                current_status=incident.status.value,
                issue_cleared=evidence.issue_cleared,
                source_asset_accessible=False,
                verification_mode=(
                    evidence.verification_mode
                ),
                signal_source=evidence.signal_source,
                message=(
                    "Resolution could not be verified because "
                    "the source asset could not be retrieved "
                    "from DataHub."
                ),
            )

        # -----------------------------------------------------
        # Detector still reports the issue
        # -----------------------------------------------------

        if not evidence.issue_cleared:
            return VerificationResult(
                incident_id=incident.incident_id,
                verified=False,
                previous_status=previous_status,
                current_status=incident.status.value,
                issue_cleared=False,
                source_asset_accessible=True,
                verification_mode=(
                    evidence.verification_mode
                ),
                signal_source=evidence.signal_source,
                message=(
                    "The incident remains open because the "
                    "detector still reports that the original "
                    "issue has not cleared."
                ),
            )

        # -----------------------------------------------------
        # Resolution verified
        # -----------------------------------------------------

        incident.mark_resolved()

        return VerificationResult(
            incident_id=incident.incident_id,
            verified=True,
            previous_status=previous_status,
            current_status=incident.status.value,
            issue_cleared=True,
            source_asset_accessible=True,
            verification_mode=(
                evidence.verification_mode
            ),
            signal_source=evidence.signal_source,
            message=(
                "The source asset is accessible and the "
                "incident detector reports that the original "
                "issue has cleared."
            ),
            post_resolution_risk_score=0,
        )