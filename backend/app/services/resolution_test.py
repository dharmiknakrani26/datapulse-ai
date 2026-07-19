import sys

from dotenv import load_dotenv
from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import (
    DataHubContext,
)
from datahub_agent_context.mcp_tools.search import (
    search,
)

from backend.app.models.resolution import (
    ResolutionEvidence,
)
from backend.app.services.datahub_writeback_service import (
    DataHubWritebackService,
)
from backend.app.services.impact_service import (
    ImpactService,
)
from backend.app.services.incident_commander_service import (
    IncidentCommanderService,
)
from backend.app.services.incident_memory_service import (
    IncidentMemoryService,
)
from backend.app.services.incident_service import (
    IncidentService,
)
from backend.app.services.investigation_service import (
    InvestigationService,
)
from backend.app.services.resolution_verification_service import (
    ResolutionVerificationService,
)


load_dotenv()


def find_connected_dataset(
    client: DataHubClient,
) -> str:

    with DataHubContext(client):
        results = search(
            query="/q orders",
            filter="entity_type = dataset",
            num_results=20,
        )

    for result in results.get(
        "searchResults",
        [],
    ):

        entity = result.get(
            "entity",
            {},
        )

        urn = entity.get(
            "urn"
        )

        if not urn:
            continue

        downstream = (
            client.lineage.get_lineage(
                source_urn=urn,
                direction="downstream",
                max_hops=3,
            )
        )

        if downstream:
            return urn

    raise RuntimeError(
        "Could not find a connected dataset."
    )


def run_resolution_test() -> None:

    client = DataHubClient.from_env()

    print()
    print(
        "=========================================="
    )
    print(
        "DataPulse AI - Resolution Verification"
    )
    print(
        "=========================================="
    )

    # ---------------------------------------------------------
    # Find test dataset
    # ---------------------------------------------------------

    dataset_urn = find_connected_dataset(
        client
    )

    # ---------------------------------------------------------
    # Create incident
    # ---------------------------------------------------------

    incident = (
        IncidentService
        .create_freshness_incident(
            asset_urn=dataset_urn
        )
    )

    # ---------------------------------------------------------
    # Investigate
    # ---------------------------------------------------------

    investigator = (
        InvestigationService(
            client
        )
    )

    investigation = (
        investigator.investigate(
            incident=incident,
            max_hops=3,
        )
    )

    # ---------------------------------------------------------
    # Calculate impact
    # ---------------------------------------------------------

    impact = ImpactService.calculate(
        incident=incident,
        investigation=investigation,
    )

    # ---------------------------------------------------------
    # AI Incident Commander
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Save active incident memory
    # ---------------------------------------------------------

    memory = (
        IncidentMemoryService()
    )

    memory.save_incident(
        incident=incident,
        investigation=investigation,
        impact=impact,
        commander=commander,
    )

    print()
    print("BEFORE RESOLUTION")
    print("------------------------------------------")

    print(
        f"Incident ID: "
        f"{incident.incident_id}"
    )

    print(
        f"Status: "
        f"{incident.status.value}"
    )

    print(
        f"Impact Score: "
        f"{impact.score}/100"
    )

    # ---------------------------------------------------------
    # Simulated detector reports recovery
    # ---------------------------------------------------------

    resolution_evidence = (
        ResolutionEvidence(
            issue_cleared=True,
            signal_source=(
                "DataPulse Demo Freshness Monitor"
            ),
            verification_mode=(
                "simulated_demo"
            ),
            details=(
                "The simulated freshness monitor "
                "now reports the source dataset "
                "as healthy."
            ),
        )
    )

    # ---------------------------------------------------------
    # Verify resolution
    # ---------------------------------------------------------

    verifier = (
        ResolutionVerificationService(
            client
        )
    )

    verification = verifier.verify(
        incident=incident,
        evidence=resolution_evidence,
    )

    if not verification.verified:
        raise RuntimeError(
            verification.message
        )

    # ---------------------------------------------------------
    # Write RESOLVED status back into DataHub
    # ---------------------------------------------------------

    writeback = (
        DataHubWritebackService()
    )

    writeback.write_incident_analysis(
        incident=incident,
        investigation=investigation,
        impact=impact,
        commander=commander,
    )

    # ---------------------------------------------------------
    # Update persistent incident memory
    # ---------------------------------------------------------

    memory.save_incident(
        incident=incident,
        investigation=investigation,
        impact=impact,
        commander=commander,
        verification=verification,
    )

    # ---------------------------------------------------------
    # Display result
    # ---------------------------------------------------------

    print()
    print("RESOLUTION VERIFICATION")
    print("------------------------------------------")

    print(
        f"Verified: "
        f"{verification.verified}"
    )

    print(
        f"Previous Status: "
        f"{verification.previous_status}"
    )

    print(
        f"Current Status: "
        f"{verification.current_status}"
    )

    print(
        f"Source Asset Accessible: "
        f"{verification.source_asset_accessible}"
    )

    print(
        f"Issue Cleared: "
        f"{verification.issue_cleared}"
    )

    print(
        f"Verification Mode: "
        f"{verification.verification_mode}"
    )

    print(
        f"Post-Resolution Risk: "
        f"{verification.post_resolution_risk_score}"
    )

    print()
    print("INCIDENT MEMORY")
    print("------------------------------------------")

    saved_incident = (
        memory.get_incident(
            incident.incident_id
        )
    )

    if not saved_incident:
        raise RuntimeError(
            "Resolved incident was not saved "
            "to incident memory."
        )

    print(
        f"Incident saved: "
        f"{incident.incident_id}"
    )

    print(
        "History file: "
        "backend/data/incident_history.json"
    )

    print()
    print(
        "=========================================="
    )
    print("Status: SUCCESS")
    print(
        "DataPulse AI verified the resolution "
        "and preserved the incident memory."
    )
    print(
        "=========================================="
    )


if __name__ == "__main__":

    try:
        run_resolution_test()

    except Exception as exc:

        print()
        print(
            "=========================================="
        )
        print("Status: FAILED")
        print(
            f"Error: {exc}"
        )
        print(
            "=========================================="
        )

        sys.exit(1)