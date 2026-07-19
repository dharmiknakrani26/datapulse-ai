import json
import sys

from dotenv import load_dotenv
from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.search import search

from backend.app.services.incident_service import IncidentService


load_dotenv()


def find_test_dataset() -> str:
    client = DataHubClient.from_env()

    with DataHubContext(client):
        results = search(
            query="/q orders",
            filter="entity_type = dataset",
            num_results=20,
        )

    search_results = results.get("searchResults", [])

    for result in search_results:
        entity = result.get("entity", {})
        urn = entity.get("urn")

        if urn:
            return urn

    raise RuntimeError(
        "Could not find a dataset for the incident test."
    )


def run_incident_test() -> None:
    print("\n==========================================")
    print("DataPulse AI - Incident System")
    print("==========================================")

    dataset_urn = find_test_dataset()

    incident = IncidentService.create_freshness_incident(
        asset_urn=dataset_urn
    )

    print("\nINCIDENT CREATED\n")

    print(
        json.dumps(
            incident.to_dict(),
            indent=2,
        )
    )

    print("\n==========================================")
    print("Status: SUCCESS")
    print("DataPulse AI can create structured incidents.")
    print("==========================================")


if __name__ == "__main__":
    try:
        run_incident_test()

    except Exception as exc:
        print("\n==========================================")
        print("Status: FAILED")
        print(f"Error: {exc}")
        print("==========================================")
        sys.exit(1)