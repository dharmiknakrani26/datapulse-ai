import json
import sys

from dotenv import load_dotenv
from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.search import search

from backend.app.services.incident_service import IncidentService
from backend.app.services.investigation_service import InvestigationService


load_dotenv()


def find_test_dataset() -> str:
    client = DataHubClient.from_env()

    with DataHubContext(client):
        results = search(
            query="/q orders",
            filter="entity_type = dataset",
            num_results=20,
        )

    for result in results.get("searchResults", []):
        entity = result.get("entity", {})
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
        "Could not find an orders dataset with downstream lineage."
    )


def run_investigation_test() -> None:
    client = DataHubClient.from_env()

    print("\n==========================================")
    print("DataPulse AI - Autonomous Investigation")
    print("==========================================")

    dataset_urn = find_test_dataset()

    incident = IncidentService.create_freshness_incident(
        asset_urn=dataset_urn,
    )

    investigator = InvestigationService(client)

    result = investigator.investigate(
        incident=incident,
        max_hops=3,
    )

    print("\nINCIDENT")
    print("------------------------------------------")
    print(f"ID: {incident.incident_id}")
    print(f"Status: {incident.status.value}")
    print(f"Source: {incident.asset_urn}")

    print("\nBLAST RADIUS")
    print("------------------------------------------")
    print(f"Upstream assets: {result.total_upstream}")
    print(f"Downstream assets: {result.total_downstream}")
    print(f"Total connected assets: {result.total_affected_assets}")

    print("\nDOWNSTREAM ASSETS")
    print("------------------------------------------")

    for asset in result.downstream_assets:
        print(
            f"- {asset.name} "
            f"| Type: {asset.asset_type} "
            f"| Platform: {asset.platform} "
            f"| Hops: {asset.hops}"
        )

    print("\nFULL INVESTIGATION RESULT")
    print("------------------------------------------")

    print(
        json.dumps(
            result.to_dict(),
            indent=2,
        )
    )

    print("\n==========================================")
    print("Status: SUCCESS")
    print("DataPulse AI created its first blast radius.")
    print("==========================================")


if __name__ == "__main__":
    try:
        run_investigation_test()

    except Exception as exc:
        print("\n==========================================")
        print("Status: FAILED")
        print(f"Error: {exc}")
        print("==========================================")
        sys.exit(1)