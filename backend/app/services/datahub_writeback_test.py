import sys

from dotenv import load_dotenv
from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.search import search

from backend.app.services.datahub_writeback_service import (
    DataHubWritebackService,
)
from backend.app.services.impact_service import (
    ImpactService,
)
from backend.app.services.incident_commander_service import (
    IncidentCommanderService,
)
from backend.app.services.incident_service import (
    IncidentService,
)
from backend.app.services.investigation_service import (
    InvestigationService,
)


load_dotenv()


def find_connected_dataset(
    client: DataHubClient,
) -> str:
    """
    Find an orders-related dataset with downstream lineage.
    """

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

        urn = entity.get("urn")

        if not urn:
            continue

        downstream = client.lineage.get_lineage(
            source_urn=urn,
            direction="downstream",
            max_hops=3,
        )

        if downstream:
            return urn

    raise RuntimeError(
        "Could not find a connected dataset."
    )


def run_writeback_test() -> None:
    """
    Run the full DataPulse pipeline and write the resulting
    incident intelligence back into DataHub.
    """

    client = DataHubClient.from_env()

    print()
    print("==========================================")
    print("DataPulse AI - DataHub Writeback")
    print("==========================================")

    # ---------------------------------------------------------
    # Find source dataset
    # ---------------------------------------------------------

    dataset_urn = find_connected_dataset(
        client
    )

    print()
    print("SOURCE DATASET")
    print("------------------------------------------")
    print(dataset_urn)

    # ---------------------------------------------------------
    # Create incident
    # ---------------------------------------------------------

    incident = (
        IncidentService.create_freshness_incident(
            asset_urn=dataset_urn
        )
    )

    # ---------------------------------------------------------
    # Investigate
    # ---------------------------------------------------------

    investigation_service = InvestigationService(
        client
    )

    investigation = (
        investigation_service.investigate(
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
    # Generate AI analysis
    # ---------------------------------------------------------

    commander_service = (
        IncidentCommanderService()
    )

    commander_result = (
        commander_service.analyze(
            incident=incident,
            investigation=investigation,
            impact=impact,
        )
    )

    # ---------------------------------------------------------
    # Write findings back to DataHub
    # ---------------------------------------------------------

    writeback_service = (
        DataHubWritebackService()
    )

    writeback_service.write_incident_analysis(
        incident=incident,
        investigation=investigation,
        impact=impact,
        commander=commander_result,
    )

    # ---------------------------------------------------------
    # Display result
    # ---------------------------------------------------------

    print()
    print("WRITEBACK RESULT")
    print("------------------------------------------")

    print(
        f"Incident ID: "
        f"{incident.incident_id}"
    )

    print(
        f"Impact Score: "
        f"{impact.score}/100"
    )

    print(
        f"Risk Level: "
        f"{impact.risk_level}"
    )

    print(
        f"Root Cause Confidence: "
        f"{commander_result.root_cause_confidence}%"
    )

    print()

    print(
        "DataPulse investigation metadata "
        "was written back to the source dataset."
    )

    print()
    print("==========================================")
    print("Status: SUCCESS")
    print(
        "DataPulse AI successfully enriched "
        "the DataHub metadata graph."
    )
    print("==========================================")


if __name__ == "__main__":
    try:
        run_writeback_test()

    except Exception as exc:
        print()
        print("==========================================")
        print("Status: FAILED")
        print(
            f"Error: {exc}"
        )
        print("==========================================")

        sys.exit(1)