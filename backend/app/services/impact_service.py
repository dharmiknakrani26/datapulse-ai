from backend.app.models.impact import (
    ImpactBreakdown,
    ImpactScore,
)
from backend.app.models.incident import (
    Incident,
    IncidentSeverity,
)
from backend.app.models.investigation import InvestigationResult


class ImpactService:
    """
    Deterministic DataPulse AI business impact scoring engine.

    Maximum score: 100

    Components:
    - Incident severity:       30
    - Blast radius:           25
    - Business exposure:      20
    - Operational complexity: 15
    - Governance risk:        10
    """

    SEVERITY_SCORES = {
        IncidentSeverity.LOW: 8,
        IncidentSeverity.MEDIUM: 16,
        IncidentSeverity.HIGH: 24,
        IncidentSeverity.CRITICAL: 30,
    }

    @classmethod
    def _score_incident_severity(
        cls,
        incident: Incident,
    ) -> int:
        return cls.SEVERITY_SCORES.get(
            incident.severity,
            16,
        )

    @staticmethod
    def _score_blast_radius(
        investigation: InvestigationResult,
    ) -> int:
        """
        Score based primarily on downstream impact.

        More downstream dependencies mean a larger blast radius.
        """

        downstream = investigation.total_downstream

        if downstream == 0:
            return 0

        if downstream <= 2:
            return 5

        if downstream <= 5:
            return 10

        if downstream <= 10:
            return 17

        if downstream <= 20:
            return 22

        return 25

    @staticmethod
    def _score_business_exposure(
        investigation: InvestigationResult,
    ) -> int:
        """
        Dashboards and business domains increase business exposure.
        """

        score = 0

        # Dashboards/charts are directly consumed by business users.
        score += min(
            investigation.affected_dashboards * 5,
            15,
        )

        # Multiple business domains increase organizational impact.
        score += min(
            len(investigation.affected_domains) * 3,
            5,
        )

        return min(score, 20)

    @staticmethod
    def _score_operational_complexity(
        investigation: InvestigationResult,
    ) -> int:
        """
        Pipelines and upstream dependencies increase remediation effort.
        """

        score = 0

        score += min(
            investigation.affected_pipelines * 4,
            8,
        )

        score += min(
            investigation.total_upstream * 2,
            7,
        )

        return min(score, 15)

    @staticmethod
    def _score_governance_risk(
        investigation: InvestigationResult,
    ) -> int:
        """
        Missing ownership and domain context make incidents harder
        to resolve and escalate.
        """

        score = 0

        if not investigation.affected_owner_names:
            score += 6

        if not investigation.affected_domains:
            score += 4

        return min(score, 10)

    @staticmethod
    def _risk_level(score: int) -> str:

        if score >= 80:
            return "CRITICAL"

        if score >= 60:
            return "HIGH"

        if score >= 35:
            return "MEDIUM"

        return "LOW"

    @staticmethod
    def _build_explanation(
        score: int,
        risk_level: str,
        investigation: InvestigationResult,
    ) -> str:

        return (
            f"This incident received a DataPulse Impact Score of "
            f"{score}/100 and is classified as {risk_level}. "
            f"The blast radius includes "
            f"{investigation.total_downstream} downstream assets, "
            f"{investigation.affected_dashboards} dashboards or charts, "
            f"{investigation.affected_pipelines} pipelines, and "
            f"{len(investigation.affected_domains)} business domains."
        )

    @classmethod
    def calculate(
        cls,
        incident: Incident,
        investigation: InvestigationResult,
    ) -> ImpactScore:

        breakdown = ImpactBreakdown(
            incident_severity=cls._score_incident_severity(
                incident
            ),
            blast_radius=cls._score_blast_radius(
                investigation
            ),
            business_exposure=cls._score_business_exposure(
                investigation
            ),
            operational_complexity=(
                cls._score_operational_complexity(
                    investigation
                )
            ),
            governance_risk=cls._score_governance_risk(
                investigation
            ),
        )

        score = breakdown.total()

        risk_level = cls._risk_level(score)

        explanation = cls._build_explanation(
            score=score,
            risk_level=risk_level,
            investigation=investigation,
        )

        return ImpactScore(
            score=score,
            risk_level=risk_level,
            breakdown=breakdown,
            explanation=explanation,
        )