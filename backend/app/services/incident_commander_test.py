import sys

from dotenv import load_dotenv
from datahub.sdk.main_client import DataHubClient
from datahub_agent_context.context import DataHubContext
from datahub_agent_context.mcp_tools.search import search

from backend.app.services.impact_service import ImpactService
from backend.app.services.incident_commander_service import (
    IncidentCommanderService,
)
from backend.app.services.incident_service import IncidentService
from backend.app.services.investigation_service import (
    InvestigationService,
)


load_dotenv()


def find_connected_dataset(
    client: DataHubClient,
) -> str:
    """
    Find an orders-related dataset that has downstream lineage.

    This gives the Incident Commander a useful blast radius
    for testing.
    """

    with DataHubContext(client):
        results = search(
            query="/q orders",
            filter="entity_type = dataset",
            num_results=20,
        )

    search_results = results.get(
        "searchResults",
        [],
    )

    for result in search_results:
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
        "Could not find an orders dataset "
        "with downstream lineage."
    )


def run_incident_commander_test() -> None:
    """
    Run the complete DataPulse AI intelligence pipeline:

    Dataset
    -> Incident
    -> Investigation
    -> Blast Radius
    -> Impact Score
    -> AI Incident Commander
    """

    client = DataHubClient.from_env()

    print()
    print("==========================================")
    print("DataPulse AI - AI Incident Commander")
    print("==========================================")

    # ---------------------------------------------------------
    # 1. Find a connected DataHub dataset
    # ---------------------------------------------------------

    dataset_urn = find_connected_dataset(
        client
    )

    print()
    print("SOURCE DATASET")
    print("------------------------------------------")
    print(dataset_urn)

    # ---------------------------------------------------------
    # 2. Create a simulated freshness incident
    # ---------------------------------------------------------

    incident = (
        IncidentService.create_freshness_incident(
            asset_urn=dataset_urn
        )
    )

    # ---------------------------------------------------------
    # 3. Investigate the DataHub graph
    # ---------------------------------------------------------

    investigator = InvestigationService(
        client
    )

    investigation = investigator.investigate(
        incident=incident,
        max_hops=3,
    )

    # ---------------------------------------------------------
    # 4. Calculate deterministic business impact
    # ---------------------------------------------------------

    impact = ImpactService.calculate(
        incident=incident,
        investigation=investigation,
    )

    # ---------------------------------------------------------
    # 5. Generate grounded AI analysis
    # ---------------------------------------------------------

    commander = IncidentCommanderService()

    analysis = commander.analyze(
        incident=incident,
        investigation=investigation,
        impact=impact,
    )

    # ---------------------------------------------------------
    # Display incident information
    # ---------------------------------------------------------

    print()
    print("INCIDENT")
    print("------------------------------------------")

    print(
        f"ID: {incident.incident_id}"
    )

    print(
        f"Type: {incident.incident_type.value}"
    )

    print(
        f"Status: {incident.status.value}"
    )

    # ---------------------------------------------------------
    # Display deterministic impact score
    # ---------------------------------------------------------

    print()
    print("DATAPULSE IMPACT SCORE")
    print("------------------------------------------")

    print(
        f"Impact Score: "
        f"{impact.score}/100"
    )

    print(
        f"Risk Level: "
        f"{impact.risk_level}"
    )

    print(
        f"Downstream Assets: "
        f"{investigation.total_downstream}"
    )

    print(
        f"Affected Dashboards: "
        f"{investigation.affected_dashboards}"
    )

    print(
        f"Affected Domains: "
        f"{len(investigation.affected_domains)}"
    )

    # ---------------------------------------------------------
    # Executive summary
    # ---------------------------------------------------------

    print()
    print("EXECUTIVE SUMMARY")
    print("------------------------------------------")

    print(
        analysis.executive_summary
    )

    # ---------------------------------------------------------
    # Business impact
    # ---------------------------------------------------------

    print()
    print("BUSINESS IMPACT")
    print("------------------------------------------")

    print(
        analysis.business_impact_summary
    )

    # ---------------------------------------------------------
    # Root-cause hypothesis
    # ---------------------------------------------------------

    print()
    print("ROOT-CAUSE HYPOTHESIS")
    print("------------------------------------------")

    print(
        analysis.root_cause_hypothesis
    )

    print()

    print(
        f"Confidence: "
        f"{analysis.root_cause_confidence}%"
    )

    # ---------------------------------------------------------
    # Evidence
    # ---------------------------------------------------------

    print()
    print("EVIDENCE")
    print("------------------------------------------")

    if analysis.evidence:
        for item in analysis.evidence:
            print(
                f"- {item}"
            )
    else:
        print(
            "No supporting evidence returned."
        )

    # ---------------------------------------------------------
    # Recommended actions
    # ---------------------------------------------------------

    print()
    print("RECOMMENDED ACTIONS")
    print("------------------------------------------")

    actions = sorted(
        analysis.recommended_actions,
        key=lambda action: action.priority,
    )

    if actions:
        for action in actions:
            print(
                f"{action.priority}. "
                f"{action.action}"
            )

            print(
                f"   Why: "
                f"{action.reason}"
            )

            print()

    else:
        print(
            "No recommended actions returned."
        )

    # ---------------------------------------------------------
    # Limitations
    # ---------------------------------------------------------

    print()
    print("LIMITATIONS")
    print("------------------------------------------")

    if analysis.limitations:
        for limitation in analysis.limitations:
            print(
                f"- {limitation}"
            )

    else:
        print(
            "No major limitations reported."
        )

    # ---------------------------------------------------------
    # Final status
    # ---------------------------------------------------------

    print()
    print("==========================================")
    print("Status: SUCCESS")
    print(
        "DataPulse AI generated a grounded "
        "incident-response analysis."
    )
    print("==========================================")


if __name__ == "__main__":

    try:
        run_incident_commander_test()

    except Exception as exc:

        print()
        print("==========================================")
        print("Status: FAILED")
        print(
            f"Error: {exc}"
        )
        print("==========================================")

        sys.exit(1)