import sys

from dotenv import load_dotenv
from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.search import search


load_dotenv()


def test_metadata_search() -> None:
    """Test DataPulse AI metadata search against DataHub."""

    client = DataHubClient.from_env()

    print("\n==========================================")
    print("DataPulse AI - DataHub Metadata Search")
    print("==========================================")

    with DataHubContext(client):
        results = search(
            query="/q orders",
            filter="entity_type = dataset",
            num_results=10,
        )

        search_results = results.get("searchResults", [])

        if not search_results:
            print("No datasets found for 'orders'.")
            print("The DataHub connection is working, but no matching assets were returned.")
            return

        print(f"Found {len(search_results)} dataset(s):\n")

        for index, result in enumerate(search_results, start=1):
            entity = result.get("entity", {})

            name = (
                entity.get("name")
                or entity.get("properties", {}).get("name")
                or "Unknown"
            )

            urn = entity.get("urn", "Unknown")

            print(f"{index}. {name}")
            print(f"   URN: {urn}")
            print()

        print("==========================================")
        print("Status: SUCCESS")
        print("DataPulse AI can search DataHub metadata.")
        print("==========================================")


if __name__ == "__main__":
    try:
        test_metadata_search()

    except Exception as exc:
        print("\n==========================================")
        print("Status: FAILED")
        print(f"Error: {exc}")
        print("==========================================")
        sys.exit(1)