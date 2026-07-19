from pydantic import BaseModel, Field


class RecommendedAction(BaseModel):
    priority: int = Field(
        ge=1,
        le=5,
        description="Action priority where 1 is the highest priority.",
    )

    action: str = Field(
        description="Specific action the data team should take."
    )

    reason: str = Field(
        description="Why this action is recommended."
    )


class IncidentCommanderResult(BaseModel):
    executive_summary: str = Field(
        description=(
            "A concise plain-English explanation of what happened "
            "and why it matters."
        )
    )

    business_impact_summary: str = Field(
        description=(
            "Explanation of the business impact based only on "
            "the supplied DataHub evidence."
        )
    )

    root_cause_hypothesis: str = Field(
        description=(
            "Most plausible root-cause hypothesis. Must clearly "
            "state when evidence is insufficient."
        )
    )

    root_cause_confidence: int = Field(
        ge=0,
        le=100,
        description="Confidence percentage for the root-cause hypothesis.",
    )

    evidence: list[str] = Field(
        description=(
            "Specific evidence from the supplied incident and "
            "DataHub investigation supporting the analysis."
        )
    )

    recommended_actions: list[RecommendedAction] = Field(
        description="Prioritized incident-response actions."
    )

    limitations: list[str] = Field(
        description=(
            "Important information that could not be verified "
            "from the supplied evidence."
        )
    )