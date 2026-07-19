import sys

from dotenv import load_dotenv
from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.search import search


load_dotenv()


def find_dataset_urn(client: DataHubClient) -> str:
    """Find a sample dataset in DataHub that has a useful chance of lineage."""

    with DataHubContext(client):
        results = search(
            query="/q orders",
            filter="entity_type = dataset",
            num_results=20,
        )

    search_results = results.get("searchResults", [])

    if not search_results:
        raise RuntimeError("No matching datasets found in DataHub.")

    for result in search_results:
        entity = result.get("entity", {})
        urn = entity.get("urn")

        if urn:
            return urn

    raise RuntimeError("Search results did not contain a dataset URN.")


def test_lineage() -> None:
    client = DataHubClient.from_env()

    print("\n==========================================")
    print("DataPulse AI - Lineage Test")
    print("==========================================")

    dataset_urn = find_dataset_urn(client)

    print(f"\nSelected dataset:\n{dataset_urn}\n")

    downstream = client.lineage.get_lineage(
        source_urn=dataset_urn,
        direction="downstream",
        max_hops=3,
    )

    upstream = client.lineage.get_lineage(
        source_urn=dataset_urn,
        direction="upstream",
        max_hops=3,
    )

    print("UPSTREAM ASSETS")
    print("------------------------------------------")

    if upstream:
        for asset in upstream:
            print(
                f"- {asset.name} "
                f"| Type: {asset.type} "
                f"| Hops: {asset.hops}"
            )
    else:
        print("No upstream lineage found.")

    print("\nDOWNSTREAM ASSETS")
    print("------------------------------------------")

    if downstream:
        for asset in downstream:
            print(
                f"- {asset.name} "
                f"| Type: {asset.type} "
                f"| Hops: {asset.hops}"
            )
    else:
        print("No downstream lineage found.")

    print("\n==========================================")
    print("Status: SUCCESS")
    print("DataPulse AI can trace DataHub lineage.")
    print("==========================================")


if __name__ == "__main__":
    try:
        test_lineage()

    except Exception as exc:
        print("\n==========================================")
        print("Status: FAILED")
        print(f"Error: {exc}")
        print("==========================================")
        sys.exit(1)