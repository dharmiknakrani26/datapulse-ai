from backend.app.models.incident import (
    Incident,
    IncidentSeverity,
    IncidentType,
)


class IncidentService:
    """
    Creates incidents for DataPulse AI.

    During the hackathon demo we can generate predictable incidents
    so judges can see the full investigation workflow end-to-end.
    Later this service can also consume real DataHub quality signals.
    """

    @staticmethod
    def create_freshness_incident(asset_urn: str) -> Incident:
        return Incident(
            title="Critical dataset freshness failure",
            asset_urn=asset_urn,
            incident_type=IncidentType.FRESHNESS,
            description=(
                "The selected dataset has not refreshed within its expected "
                "update window. Downstream datasets, dashboards, and business "
                "reports may contain stale information."
            ),
            severity=IncidentSeverity.HIGH,
        )

    @staticmethod
    def create_data_quality_incident(asset_urn: str) -> Incident:
        return Incident(
            title="Data quality failure detected",
            asset_urn=asset_urn,
            incident_type=IncidentType.DATA_QUALITY,
            description=(
                "The selected dataset has failed one or more data quality "
                "checks and may be unsafe for downstream analytics."
            ),
            severity=IncidentSeverity.HIGH,
        )

    @staticmethod
    def create_schema_change_incident(asset_urn: str) -> Incident:
        return Incident(
            title="Unexpected schema change detected",
            asset_urn=asset_urn,
            incident_type=IncidentType.SCHEMA_CHANGE,
            description=(
                "A structural change was detected in the selected dataset. "
                "Downstream transformations and dashboards may be affected."
            ),
            severity=IncidentSeverity.MEDIUM,
        )