import sys

from dotenv import load_dotenv
from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.search import search

from backend.app.services.incident_service import IncidentService
from backend.app.services.investigation_service import InvestigationService


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
        "Could not find a connected dataset."
    )


def run_business_context_test() -> None:

    client = DataHubClient.from_env()

    print("\n==========================================")
    print("DataPulse AI - Business Context Analysis")
    print("==========================================")

    dataset_urn = find_connected_dataset(client)

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
    print(f"Source: {incident.asset_urn}")

    print("\nBUSINESS BLAST RADIUS")
    print("------------------------------------------")

    print(
        f"Total affected assets: "
        f"{result.total_affected_assets}"
    )

    print(
        f"Affected datasets: "
        f"{result.affected_datasets}"
    )

    print(
        f"Affected dashboards/charts: "
        f"{result.affected_dashboards}"
    )

    print(
        f"Affected pipelines: "
        f"{result.affected_pipelines}"
    )

    print("\nAFFECTED DOMAINS")
    print("------------------------------------------")

    if result.affected_domains:
        for domain in result.affected_domains:
            print(f"- {domain}")
    else:
        print("No domain metadata found.")

    print("\nRESPONSIBLE OWNERS")
    print("------------------------------------------")

    if result.affected_owner_names:
        for owner in result.affected_owner_names:
            print(f"- {owner}")
    else:
        print("No owner metadata found.")

    print("\nDOWNSTREAM ASSETS")
    print("------------------------------------------")

    for asset in result.downstream_assets:

        owners = (
            ", ".join(asset.owner_names)
            if asset.owner_names
            else "No owner"
        )

        domain = asset.domain_name or "No domain"

        print(
            f"- {asset.name}\n"
            f"  Type: {asset.asset_type}\n"
            f"  Platform: {asset.platform}\n"
            f"  Hops: {asset.hops}\n"
            f"  Domain: {domain}\n"
            f"  Owners: {owners}\n"
        )

    print("==========================================")
    print("Status: SUCCESS")
    print(
        "DataPulse AI understands the business "
        "context of its blast radius."
    )
    print("==========================================")


if __name__ == "__main__":

    try:
        run_business_context_test()

    except Exception as exc:

        print("\n==========================================")
        print("Status: FAILED")
        print(f"Error: {exc}")
        print("==========================================")

        sys.exit(1)