import json
from pathlib import Path
from typing import Optional

from backend.app.models.commander import (
    IncidentCommanderResult,
)
from backend.app.models.impact import ImpactScore
from backend.app.models.incident import Incident
from backend.app.models.investigation import (
    InvestigationResult,
)
from backend.app.models.resolution import (
    VerificationResult,
)


class IncidentMemoryService:
    """
    Persistent incident memory for DataPulse AI.

    Stores the latest full state for each incident so future
    users and future agent workflows can inspect what happened,
    what DataPulse discovered, and how the incident ended.
    """

    def __init__(
        self,
        storage_path: str = (
            "backend/data/incident_history.json"
        ),
    ) -> None:

        self.storage_path = Path(
            storage_path
        )

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _load_records(
        self,
    ) -> list[dict]:

        if not self.storage_path.exists():
            return []

        content = (
            self.storage_path
            .read_text(
                encoding="utf-8"
            )
            .strip()
        )

        if not content:
            return []

        data = json.loads(
            content
        )

        if not isinstance(
            data,
            list,
        ):
            raise RuntimeError(
                "Incident memory file must "
                "contain a JSON list."
            )

        return data

    def _save_records(
        self,
        records: list[dict],
    ) -> None:
        """
        Write using a temporary file first to reduce the risk
        of corrupting the main incident-memory file.
        """

        temporary_path = (
            self.storage_path.with_suffix(
                ".tmp"
            )
        )

        temporary_path.write_text(
            json.dumps(
                records,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(
            self.storage_path
        )

    def save_incident(
        self,
        incident: Incident,
        investigation: InvestigationResult,
        impact: ImpactScore,
        commander: IncidentCommanderResult,
        verification: Optional[
            VerificationResult
        ] = None,
    ) -> None:

        records = self._load_records()

        record = {
            "incident": (
                incident.to_dict()
            ),

            "investigation": (
                investigation.to_dict()
            ),

            "impact": (
                impact.to_dict()
            ),

            "commander_analysis": (
                commander.model_dump()
            ),

            "resolution_verification": (
                verification.to_dict()
                if verification
                else None
            ),
        }

        existing_index = None

        for index, existing in enumerate(
            records
        ):
            existing_incident = (
                existing.get(
                    "incident",
                    {},
                )
            )

            if (
                existing_incident.get(
                    "incident_id"
                )
                == incident.incident_id
            ):
                existing_index = index
                break

        if existing_index is None:
            records.append(
                record
            )

        else:
            records[
                existing_index
            ] = record

        self._save_records(
            records
        )

    def get_incident(
        self,
        incident_id: str,
    ) -> dict | None:

        records = self._load_records()

        for record in records:
            incident = record.get(
                "incident",
                {},
            )

            if (
                incident.get(
                    "incident_id"
                )
                == incident_id
            ):
                return record

        return None

    def get_all_incidents(
        self,
    ) -> list[dict]:

        return self._load_records()