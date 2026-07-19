import os
from datetime import datetime, timezone

from datahub.sdk.main_client import DataHubClient
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from backend.app.api.schemas import (
    CreateIncidentRequest,
    ResolveIncidentRequest,
)
from backend.app.services.incident_workflow_service import (
    IncidentWorkflowService,
)


load_dotenv()


router = APIRouter(
    prefix="/api",
    tags=["DataPulse AI"],
)


# =============================================================
# System Health
# =============================================================


@router.get("/health")
def health_check() -> dict:

    return {
        "status": "healthy",
        "service": "DataPulse AI API",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


@router.get("/system/status")
def system_status() -> dict:

    datahub_connected = False
    datahub_error = None

    try:
        client = DataHubClient.from_env()

        client.test_connection()

        datahub_connected = True

    except Exception as exc:
        datahub_error = str(exc)

    return {
        "datapulse_api": "online",

        "datahub": {
            "connected": datahub_connected,

            "server": os.getenv(
                "DATAHUB_GMS_URL",
                "http://localhost:8080",
            ),

            "error": datahub_error,
        },

        "ai": {
            "provider": os.getenv(
                "LLM_PROVIDER",
                "not_configured",
            ),

            "model": os.getenv(
                "LLM_MODEL",
                "not_configured",
            ),

            "api_key_configured": bool(
                os.getenv(
                    "LLM_API_KEY",
                    "",
                ).strip()
            ),
        },

        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# =============================================================
# Asset Discovery
# =============================================================


@router.get("/assets/search")
def search_assets(
    q: str = Query(
        default="orders",
        min_length=1,
        max_length=100,
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
) -> dict:

    try:
        workflow = (
            IncidentWorkflowService()
        )

        assets = workflow.search_assets(
            query=q,
            limit=limit,
        )

        return {
            "query": q,
            "count": len(assets),
            "assets": assets,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# =============================================================
# Analyze Incident
# =============================================================


@router.post("/incidents/analyze")
def analyze_incident(
    request: CreateIncidentRequest,
) -> dict:
    """
    Run the complete autonomous DataPulse investigation pipeline.
    """

    try:
        workflow = (
            IncidentWorkflowService()
        )

        result = (
            workflow.analyze_incident(
                asset_urn=request.asset_urn,

                search_query=(
                    request.search_query
                ),

                incident_type=(
                    request.incident_type
                ),

                max_hops=request.max_hops,
            )
        )

        return {
            "status": "success",

            "message": (
                "DataPulse AI completed "
                "the incident investigation."
            ),

            "result": result,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# =============================================================
# Incident History
# =============================================================


@router.get("/incidents")
def get_incident_history() -> dict:

    try:
        workflow = (
            IncidentWorkflowService()
        )

        incidents = (
            workflow.get_all_incidents()
        )

        return {
            "count": len(incidents),
            "incidents": incidents,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.get("/incidents/{incident_id}")
def get_incident(
    incident_id: str,
) -> dict:

    try:
        workflow = (
            IncidentWorkflowService()
        )

        incident = (
            workflow.get_incident(
                incident_id
            )
        )

        if not incident:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Incident not found: "
                    f"{incident_id}"
                ),
            )

        return incident

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
@router.get(
    "/incidents/{incident_id}/lineage-graph"
)
def get_incident_lineage_graph(
    incident_id: str,
) -> dict:

    try:
        workflow = (
            IncidentWorkflowService()
        )

        graph = (
            workflow
            .get_lineage_graph(
                incident_id
            )
        )

        return {
            "status": "success",
            "graph": graph,
        }

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

# =============================================================
# Resolve Incident
# =============================================================


@router.post(
    "/incidents/{incident_id}/resolve"
)
def resolve_incident(
    incident_id: str,
    request: ResolveIncidentRequest,
) -> dict:

    try:
        workflow = (
            IncidentWorkflowService()
        )

        result = (
            workflow.resolve_incident(
                incident_id=incident_id,

                issue_cleared=(
                    request.issue_cleared
                ),

                signal_source=(
                    request.signal_source
                ),

                details=request.details,

                verification_mode=(
                    request.verification_mode
                ),
            )
        )

        verification = (
            result.get(
                "resolution_verification"
            )
            or {}
        )

        return {
            "status": "success",

            "verified": verification.get(
                "verified",
                False,
            ),

            "message": verification.get(
                "message",
                "Resolution workflow completed.",
            ),

            "result": result,
        }

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc