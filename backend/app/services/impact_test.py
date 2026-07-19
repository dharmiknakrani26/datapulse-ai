import json
import sys

from dotenv import load_dotenv
from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.search import search

from backend.app.services.impact_service import ImpactService
from backend.app.services.incident_service import IncidentService
from backend.app.services.investigation_service import (
    InvestigationService,
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


def run_impact_test() -> None:

    client = DataHubClient.from_env()

    print("\n==========================================")
    print("DataPulse AI - Impact Scoring Engine")
    print("==========================================")

    dataset_urn = find_connected_dataset(
        client
    )

    incident = (
        IncidentService.create_freshness_incident(
            asset_urn=dataset_urn
        )
    )

    investigator = InvestigationService(
        client
    )

    investigation = investigator.investigate(
        incident=incident,
        max_hops=3,
    )

    impact = ImpactService.calculate(
        incident=incident,
        investigation=investigation,
    )

    print("\nINCIDENT")
    print("------------------------------------------")
    print(
        f"ID: {incident.incident_id}"
    )
    print(
        f"Type: {incident.incident_type.value}"
    )

    print("\nDATAPULSE IMPACT SCORE")
    print("------------------------------------------")

    print(
        f"Score: {impact.score}/100"
    )

    print(
        f"Risk Level: {impact.risk_level}"
    )

    print("\nSCORE BREAKDOWN")
    print("------------------------------------------")

    print(
        f"Incident Severity: "
        f"{impact.breakdown.incident_severity}/30"
    )

    print(
        f"Blast Radius: "
        f"{impact.breakdown.blast_radius}/25"
    )

    print(
        f"Business Exposure: "
        f"{impact.breakdown.business_exposure}/20"
    )

    print(
        f"Operational Complexity: "
        f"{impact.breakdown.operational_complexity}/15"
    )

    print(
        f"Governance Risk: "
        f"{impact.breakdown.governance_risk}/10"
    )

    print("\nANALYSIS")
    print("------------------------------------------")

    print(
        impact.explanation
    )

    print("\nFULL RESULT")
    print("------------------------------------------")

    print(
        json.dumps(
            impact.to_dict(),
            indent=2,
        )
    )

    print("\n==========================================")
    print("Status: SUCCESS")
    print(
        "DataPulse AI calculated its first "
        "business impact score."
    )
    print("==========================================")


if __name__ == "__main__":

    try:
        run_impact_test()

    except Exception as exc:

        print("\n==========================================")
        print("Status: FAILED")
        print(
            f"Error: {exc}"
        )
        print("==========================================")

        sys.exit(1)