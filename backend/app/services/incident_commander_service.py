import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from backend.app.models.commander import IncidentCommanderResult
from backend.app.models.impact import ImpactScore
from backend.app.models.incident import Incident
from backend.app.models.investigation import InvestigationResult


load_dotenv()


class IncidentCommanderService:
    """
    DataPulse AI Incident Commander.

    Converts grounded DataHub investigation evidence into:

    - Executive incident summary
    - Business impact explanation
    - Root-cause hypothesis
    - Supporting evidence
    - Prioritized response plan
    - Known limitations

    The LLM is not allowed to modify the deterministic
    DataPulse Impact Score or invent unsupported evidence.

    Temporary Gemini availability errors are retried automatically
    using exponential backoff.
    """

    def __init__(self) -> None:
        api_key = os.getenv(
            "LLM_API_KEY",
            "",
        ).strip()

        if not api_key:
            raise RuntimeError(
                "LLM_API_KEY is missing from the .env file."
            )

        self.model = os.getenv(
            "LLM_MODEL",
            "gemini-2.5-flash",
        ).strip()

        self.client = genai.Client(
            api_key=api_key,
        )

    @staticmethod
    def _compact_asset(
        asset: Any,
    ) -> dict:
        """
        Convert an affected asset into a compact representation
        suitable for sending to the LLM.
        """

        return {
            "name": asset.name,
            "urn": asset.urn,
            "type": asset.asset_type,
            "platform": asset.platform,
            "hops": asset.hops,
            "direction": asset.direction,
            "domain": asset.domain_name,
            "owners": asset.owner_names,
        }

    def _build_evidence_context(
        self,
        incident: Incident,
        investigation: InvestigationResult,
        impact: ImpactScore,
    ) -> dict:
        """
        Build the grounded evidence package sent to Gemini.

        Assets closest to the incident are prioritized because they
        are generally more relevant for incident investigation.
        """

        upstream = sorted(
            investigation.upstream_assets,
            key=lambda asset: asset.hops,
        )[:20]

        downstream = sorted(
            investigation.downstream_assets,
            key=lambda asset: asset.hops,
        )[:25]

        return {
            "incident": {
                "id": incident.incident_id,
                "title": incident.title,
                "type": incident.incident_type.value,
                "reported_severity": incident.severity.value,
                "status": incident.status.value,
                "description": incident.description,
                "source_asset_urn": incident.asset_urn,
            },

            "deterministic_impact_analysis": {
                "impact_score": impact.score,
                "risk_level": impact.risk_level,
                "score_breakdown": (
                    impact.breakdown.to_dict()
                ),
                "explanation": impact.explanation,
            },

            "blast_radius": {
                "total_upstream": (
                    investigation.total_upstream
                ),
                "total_downstream": (
                    investigation.total_downstream
                ),
                "total_affected_assets": (
                    investigation.total_affected_assets
                ),
                "affected_datasets": (
                    investigation.affected_datasets
                ),
                "affected_dashboards": (
                    investigation.affected_dashboards
                ),
                "affected_pipelines": (
                    investigation.affected_pipelines
                ),
                "affected_domains": (
                    investigation.affected_domains
                ),
                "affected_owners": (
                    investigation.affected_owner_names
                ),
            },

            "upstream_evidence": [
                self._compact_asset(asset)
                for asset in upstream
            ],

            "downstream_evidence": [
                self._compact_asset(asset)
                for asset in downstream
            ],
        }

    @staticmethod
    def _is_temporary_error(
        error: Exception,
    ) -> bool:
        """
        Detect temporary Gemini errors that are safe to retry.
        """

        error_message = str(
            error
        ).lower()

        retryable_messages = (
            "503",
            "unavailable",
            "high demand",
            "temporarily unavailable",
            "service unavailable",
            "429",
            "resource_exhausted",
            "resource exhausted",
            "rate limit",
        )

        return any(
            message in error_message
            for message in retryable_messages
        )

    def _generate_response(
        self,
        prompt: str,
    ) -> IncidentCommanderResult:
        """
        Send the grounded prompt to Gemini and validate the
        structured response.
        """

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=IncidentCommanderResult,
                temperature=0.2,
            ),
        )

        # Preferred path:
        # Gemini returns an already parsed structured response.
        if response.parsed is not None:

            if isinstance(
                response.parsed,
                IncidentCommanderResult,
            ):
                return response.parsed

            return (
                IncidentCommanderResult.model_validate(
                    response.parsed
                )
            )

        # Fallback path:
        # Validate raw JSON response manually.
        if response.text:

            return (
                IncidentCommanderResult.model_validate_json(
                    response.text
                )
            )

        raise RuntimeError(
            "Gemini returned an empty "
            "Incident Commander response."
        )

    def analyze(
        self,
        incident: Incident,
        investigation: InvestigationResult,
        impact: ImpactScore,
    ) -> IncidentCommanderResult:
        """
        Generate a grounded AI incident analysis.

        Temporary Gemini capacity or rate-limit errors are retried
        automatically using exponential backoff.
        """

        evidence_context = (
            self._build_evidence_context(
                incident=incident,
                investigation=investigation,
                impact=impact,
            )
        )

        prompt = f"""
You are DataPulse AI, an enterprise Data Incident Commander.

Your responsibility is to analyze a data incident using ONLY
the evidence supplied below.

STRICT ANALYSIS RULES:

1. Never invent datasets, dashboards, pipelines, owners,
   domains, timestamps, monetary values, failures, or
   technical causes.

2. The DataPulse Impact Score is deterministic and
   authoritative. Never recalculate it, modify it, or
   assign a different risk level.

3. Clearly distinguish VERIFIED EVIDENCE from HYPOTHESES.

4. A lineage relationship does not prove that an upstream
   asset caused the incident.

5. If the evidence cannot confirm a root cause, explicitly
   state that the root cause is not confirmed.

6. If root-cause evidence is weak or only based on lineage,
   root_cause_confidence must be 40 or lower.

7. Never claim that a pipeline failed unless pipeline failure
   evidence is explicitly provided.

8. Recommended actions must be practical and directly
   connected to the supplied evidence.

9. Investigation and verification must come before destructive
   or irreversible remediation actions.

10. Write clearly enough for both technical data teams and
    business stakeholders.

11. The executive summary should explain:
    - What happened
    - How serious it is
    - Why the business should care

12. The business impact explanation should reference the
    supplied blast-radius facts where relevant.

13. Recommended actions should be ordered by priority.

14. Do not claim that the simulated freshness incident itself
    has been independently verified unless explicit detector
    evidence is supplied.

DATAHUB INCIDENT EVIDENCE:

{json.dumps(
    evidence_context,
    indent=2,
    default=str,
)}

Return the analysis using the required structured response schema.
"""

        max_attempts = 5

        for attempt in range(
            1,
            max_attempts + 1,
        ):

            try:
                return self._generate_response(
                    prompt
                )

            except Exception as exc:

                if not self._is_temporary_error(
                    exc
                ):
                    raise

                if attempt >= max_attempts:
                    raise RuntimeError(
                        "Gemini remained unavailable after "
                        f"{max_attempts} attempts. "
                        "Please retry the operation later."
                    ) from exc

                wait_seconds = min(
                    2 ** attempt,
                    30,
                )

                print(
                    "\nGemini temporarily unavailable."
                )

                print(
                    f"Retrying in {wait_seconds} seconds..."
                )

                print(
                    f"Attempt "
                    f"{attempt + 1}/{max_attempts}"
                )

                time.sleep(
                    wait_seconds
                )

        raise RuntimeError(
            "Incident Commander could not "
            "generate a response."
        )