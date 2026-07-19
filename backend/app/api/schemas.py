from typing import Literal

from pydantic import BaseModel, Field


class CreateIncidentRequest(BaseModel):
    """
    Request for running a complete DataPulse incident investigation.

    If asset_urn is omitted, DataPulse automatically finds a connected
    dataset using search_query.
    """

    asset_urn: str | None = None

    search_query: str = Field(
        default="orders",
        min_length=1,
        max_length=100,
    )

    incident_type: Literal[
        "freshness",
        "data_quality",
        "schema_change",
    ] = "freshness"

    max_hops: int = Field(
        default=3,
        ge=1,
        le=5,
    )


class ResolveIncidentRequest(BaseModel):
    """
    Resolution evidence supplied to DataPulse.

    The current hackathon demo uses an explicit simulated detector signal.
    """

    issue_cleared: bool = True

    signal_source: str = Field(
        default="DataPulse Demo Monitor",
        min_length=1,
        max_length=200,
    )

    details: str = Field(
        default=(
            "The monitoring system reports that "
            "the original incident condition has cleared."
        ),
        min_length=1,
        max_length=1000,
    )

    verification_mode: str = Field(
        default="simulated_demo",
        min_length=1,
        max_length=100,
    )