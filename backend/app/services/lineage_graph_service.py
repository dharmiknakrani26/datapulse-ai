from typing import Any

from datahub.sdk.main_client import DataHubClient

from backend.app.models.investigation import InvestigationResult


class LineageGraphService:
    """
    Builds an exact visualization graph from DataHub lineage.

    The existing InvestigationResult tells us which assets belong
    to the incident blast radius.

    To avoid drawing fake relationships, this service asks DataHub
    for direct 1-hop downstream relationships between those assets.

    Output format:

    {
        "nodes": [...],
        "edges": [...]
    }
    """

    def __init__(
        self,
        client: DataHubClient,
    ) -> None:
        self.client = client

    @staticmethod
    def _normalize_type(
        asset_type: str,
    ) -> str:

        return (
            str(asset_type)
            .upper()
            .replace(
                "ENTITYTYPE.",
                "",
            )
        )

    @staticmethod
    def _node_category(
        asset_type: str,
    ) -> str:

        normalized = (
            LineageGraphService
            ._normalize_type(
                asset_type
            )
        )

        if "DATASET" in normalized:
            return "dataset"

        if (
            "DASHBOARD" in normalized
            or "CHART" in normalized
        ):
            return "dashboard"

        if (
            "DATAJOB" in normalized
            or "DATAFLOW" in normalized
            or "PIPELINE" in normalized
        ):
            return "pipeline"

        return "other"

    @staticmethod
    def _short_name_from_urn(
        urn: str,
    ) -> str:

        if not urn:
            return "Unknown Asset"

        try:
            parts = urn.split(",")

            if len(parts) >= 2:
                return (
                    parts[-2]
                    .replace(
                        ")",
                        "",
                    )
                    .strip()
                )

        except Exception:
            pass

        return urn

    def build_graph(
        self,
        source_asset_urn: str,
        investigation: InvestigationResult,
    ) -> dict[str, Any]:

        nodes_by_urn: dict[
            str,
            dict,
        ] = {}

        # -----------------------------------------------------
        # Source Incident Node
        # -----------------------------------------------------

        nodes_by_urn[
            source_asset_urn
        ] = {
            "id": source_asset_urn,

            "name": (
                self._short_name_from_urn(
                    source_asset_urn
                )
            ),

            "asset_type": "DATASET",

            "category": "incident",

            "platform": "unknown",

            "direction": "source",

            "hops": 0,

            "domain": None,

            "owners": [],

            "is_incident_source": True,
        }

        # -----------------------------------------------------
        # Add Investigation Assets
        # -----------------------------------------------------

        all_assets = (
            investigation.upstream_assets
            + investigation.downstream_assets
        )

        for asset in all_assets:

            nodes_by_urn[
                asset.urn
            ] = {
                "id": asset.urn,

                "name": (
                    asset.name
                    or self._short_name_from_urn(
                        asset.urn
                    )
                ),

                "asset_type": (
                    self._normalize_type(
                        asset.asset_type
                    )
                ),

                "category": (
                    self._node_category(
                        asset.asset_type
                    )
                ),

                "platform": (
                    asset.platform
                    or "unknown"
                ),

                "direction": (
                    asset.direction
                ),

                "hops": (
                    asset.hops
                ),

                "domain": (
                    asset.domain_name
                ),

                "owners": (
                    asset.owner_names
                ),

                "is_incident_source": False,
            }

        allowed_urns = set(
            nodes_by_urn.keys()
        )

        edges_by_id: dict[
            str,
            dict,
        ] = {}

        # -----------------------------------------------------
        # Query Direct Relationships
        # -----------------------------------------------------

        for source_urn in allowed_urns:

            try:
                direct_downstream = (
                    self.client
                    .lineage
                    .get_lineage(
                        source_urn=(
                            source_urn
                        ),
                        direction=(
                            "downstream"
                        ),
                        max_hops=1,
                        count=500,
                    )
                )

            except Exception:
                # One unsupported entity should not break
                # the complete visualization.
                continue

            for result in direct_downstream:

                target_urn = str(
                    getattr(
                        result,
                        "urn",
                        "",
                    )
                )

                if (
                    not target_urn
                    or target_urn
                    not in allowed_urns
                    or target_urn
                    == source_urn
                ):
                    continue

                edge_id = (
                    f"{source_urn}"
                    f"->{target_urn}"
                )

                edges_by_id[
                    edge_id
                ] = {
                    "id": edge_id,

                    "source": (
                        source_urn
                    ),

                    "target": (
                        target_urn
                    ),
                }

        # -----------------------------------------------------
        # Fallback Edges
        #
        # In rare cases, an entity type may not expose direct
        # lineage through this SDK call. We only connect the
        # incident source to a first-hop asset when DataHub's
        # existing hop information proves it is directly related.
        # -----------------------------------------------------

        for asset in all_assets:

            if asset.hops != 1:
                continue

            if (
                asset.direction
                == "upstream"
            ):
                source = asset.urn
                target = (
                    source_asset_urn
                )

            else:
                source = (
                    source_asset_urn
                )
                target = asset.urn

            edge_id = (
                f"{source}"
                f"->{target}"
            )

            if (
                edge_id
                not in edges_by_id
            ):
                edges_by_id[
                    edge_id
                ] = {
                    "id": edge_id,
                    "source": source,
                    "target": target,
                }

        return {
            "source_asset_urn": (
                source_asset_urn
            ),

            "node_count": len(
                nodes_by_urn
            ),

            "edge_count": len(
                edges_by_id
            ),

            "nodes": list(
                nodes_by_urn.values()
            ),

            "edges": list(
                edges_by_id.values()
            ),
        }