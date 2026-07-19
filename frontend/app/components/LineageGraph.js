"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";

import styles from "./LineageGraph.module.css";

import {
  getAssetDisplayName,
} from "../utils/assetDisplay";


const API_BASE =
  "http://localhost:8000";

const NODE_WIDTH = 225;
const NODE_HEIGHT = 90;

const COLUMN_SPACING = 340;
const ROW_SPACING = 125;
const CANVAS_PADDING = 180;

const MIN_ZOOM = 0.35;
const MAX_ZOOM = 1.5;
const DEFAULT_ZOOM = 0.75;


/* =========================================================
   Custom Asset Node
========================================================= */

function AssetNode({ data }) {
  const category =
    data.is_incident_source
      ? "incident"
      : data.category || "other";

  const displayName =
    getAssetDisplayName(
      data.name,
      data.id
    );

  return (
    <div
      className={`${styles.node} ${
        styles[category] ||
        styles.other
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className={styles.handle}
      />

      <div className={styles.nodeTop}>
        <span className={styles.nodeType}>
          {data.is_incident_source
            ? "INCIDENT SOURCE"
            : String(
                data.asset_type ||
                  data.category ||
                  "ASSET"
              ).toUpperCase()}
        </span>

        {Number(data.hops) > 0 && (
          <span className={styles.hopBadge}>
            {data.hops}{" "}
            {Number(data.hops) === 1
              ? "hop"
              : "hops"}
          </span>
        )}
      </div>

      <strong
        className={styles.nodeName}
        title={displayName}
      >
        {displayName}
      </strong>

      <div className={styles.nodeMeta}>
        {data.platform &&
          data.platform !==
            "unknown" && (
            <span>
              {data.platform}
            </span>
          )}

        {data.domain && (
          <span>
            {data.domain}
          </span>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className={styles.handle}
      />
    </div>
  );
}


/*
  IMPORTANT:
  Keep nodeTypes outside the main component.
  This prevents the React Flow warning about
  recreating nodeTypes on every render.
*/

const nodeTypes = {
  assetNode: AssetNode,
};


/* =========================================================
   Build Graph Layout
========================================================= */

function buildLayout(
  graphNodes
) {
  if (!graphNodes?.length) {
    return {
      nodes: [],

      canvas: {
        width: 1600,
        height: 1000,
        sourceX: 800,
        sourceY: 500,
      },
    };
  }


  const groups = {};

  let maxUpstreamHops = 0;
  let maxDownstreamHops = 0;


  graphNodes.forEach(
    (node) => {
      let direction =
        node.direction ||
        "downstream";

      let hops =
        Number(
          node.hops || 0
        );


      if (
        node.is_incident_source
      ) {
        direction = "source";

        hops = 0;
      }


      if (
        direction ===
        "upstream"
      ) {
        maxUpstreamHops =
          Math.max(
            maxUpstreamHops,
            hops
          );
      }


      if (
        direction ===
        "downstream"
      ) {
        maxDownstreamHops =
          Math.max(
            maxDownstreamHops,
            hops
          );
      }


      const key =
        `${direction}-${hops}`;


      if (!groups[key]) {
        groups[key] = [];
      }


      groups[key].push(
        node
      );
    }
  );


  const largestGroupSize =
    Math.max(
      1,

      ...Object.values(
        groups
      ).map(
        (group) =>
          group.length
      )
    );


  const requiredColumns =
    maxUpstreamHops +
    maxDownstreamHops;


  const canvasWidth =
    Math.max(
      1800,

      CANVAS_PADDING * 2 +
        requiredColumns *
          COLUMN_SPACING +
        NODE_WIDTH
    );


  const canvasHeight =
    Math.max(
      1100,

      CANVAS_PADDING * 2 +
        largestGroupSize *
          ROW_SPACING
    );


  const sourceX =
    CANVAS_PADDING +
    maxUpstreamHops *
      COLUMN_SPACING;


  const sourceY =
    canvasHeight / 2 -
    NODE_HEIGHT / 2;


  const positionedNodes = [];


  Object.entries(
    groups
  ).forEach(
    ([key, group]) => {
      const separatorIndex =
        key.lastIndexOf("-");


      const direction =
        key.slice(
          0,
          separatorIndex
        );


      const hops =
        Number(
          key.slice(
            separatorIndex + 1
          )
        );


      let x = sourceX;


      if (
        direction ===
        "upstream"
      ) {
        x =
          sourceX -
          hops *
            COLUMN_SPACING;
      }


      if (
        direction ===
        "downstream"
      ) {
        x =
          sourceX +
          hops *
            COLUMN_SPACING;
      }


      if (
        direction ===
        "source"
      ) {
        x = sourceX;
      }


      const groupHeight =
        (group.length - 1) *
        ROW_SPACING;


      const startingY =
        sourceY -
        groupHeight / 2;


      group.forEach(
        (
          node,
          index
        ) => {
          positionedNodes.push(
            {
              id: node.id,

              type:
                "assetNode",

              position: {
                x,

                y:
                  startingY +
                  index *
                    ROW_SPACING,
              },

              data: node,
            }
          );
        }
      );
    }
  );


  return {
    nodes:
      positionedNodes,

    canvas: {
      width:
        canvasWidth,

      height:
        canvasHeight,

      sourceX,

      sourceY,
    },
  };
}


/* =========================================================
   Build Graph Edges
========================================================= */

function buildEdges(
  graphEdges,
  sourceAssetUrn
) {
  return graphEdges.map(
    (edge) => ({
      id: edge.id,

      source:
        edge.source,

      target:
        edge.target,

      type:
        "smoothstep",

      animated:
        edge.source ===
          sourceAssetUrn ||
        edge.target ===
          sourceAssetUrn,

      markerEnd: {
        type:
          MarkerType.ArrowClosed,
      },

      style: {
        strokeWidth: 1.2,
      },
    })
  );
}


/* =========================================================
   Main Component
========================================================= */

export default function LineageGraph({
  incidentId,
}) {
  const scrollAreaRef =
    useRef(null);


  const [
    nodes,
    setNodes,
    onNodesChange,
  ] = useNodesState([]);


  const [
    edges,
    setEdges,
    onEdgesChange,
  ] = useEdgesState([]);


  const [
    graph,
    setGraph,
  ] = useState(null);


  const [
    selectedNode,
    setSelectedNode,
  ] = useState(null);


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    error,
    setError,
  ] = useState("");


  const [
    zoom,
    setZoom,
  ] = useState(
    DEFAULT_ZOOM
  );


  const [
    canvas,
    setCanvas,
  ] = useState({
    width: 1800,

    height: 1100,

    sourceX: 900,

    sourceY: 550,
  });


  /* =======================================================
     Load Graph
  ======================================================= */

  useEffect(() => {
    if (!incidentId) {
      return;
    }


    const controller =
      new AbortController();


    async function loadGraph() {
      setLoading(true);

      setError("");

      setSelectedNode(
        null
      );


      try {
        const response =
          await fetch(
            `${API_BASE}/api/incidents/${incidentId}/lineage-graph`,

            {
              signal:
                controller.signal,
            }
          );


        const data =
          await response.json();


        if (
          !response.ok
        ) {
          throw new Error(
            data.detail ||
              "Could not load lineage graph."
          );
        }


        const graphData =
          data.graph;


        const layout =
          buildLayout(
            graphData.nodes ||
              []
          );


        setGraph(
          graphData
        );


        setCanvas(
          layout.canvas
        );


        setNodes(
          layout.nodes
        );


        setEdges(
          buildEdges(
            graphData.edges ||
              [],

            graphData
              .source_asset_urn
          )
        );


        setZoom(
          DEFAULT_ZOOM
        );
      } catch (
        requestError
      ) {
        if (
          requestError.name ===
          "AbortError"
        ) {
          return;
        }


        setError(
          requestError.message ||
            "Could not load lineage graph."
        );
      } finally {
        setLoading(
          false
        );
      }
    }


    loadGraph();


    return () => {
      controller.abort();
    };
  }, [
    incidentId,
    setNodes,
    setEdges,
  ]);


  /* =======================================================
     Center Incident
  ======================================================= */

  const centerIncident =
    useCallback(() => {
      const container =
        scrollAreaRef.current;


      if (
        !container
      ) {
        return;
      }


      const incidentCenterX =
        (
          canvas.sourceX +
          NODE_WIDTH / 2
        ) *
        zoom;


      const incidentCenterY =
        (
          canvas.sourceY +
          NODE_HEIGHT / 2
        ) *
        zoom;


      const left =
        incidentCenterX -
        container.clientWidth /
          2;


      const top =
        incidentCenterY -
        container.clientHeight /
          2;


      container.scrollTo({
        left:
          Math.max(
            0,
            left
          ),

        top:
          Math.max(
            0,
            top
          ),

        behavior:
          "smooth",
      });
    }, [
      canvas,
      zoom,
    ]);


  /* =======================================================
     Auto-Center Incident
  ======================================================= */

  useEffect(() => {
    if (
      loading ||
      error ||
      nodes.length === 0
    ) {
      return;
    }


    const timeout =
      setTimeout(
        () => {
          centerIncident();
        },
        150
      );


    return () => {
      clearTimeout(
        timeout
      );
    };
  }, [
    incidentId,
    loading,
    error,
    nodes.length,
    centerIncident,
  ]);


  /* =======================================================
     Custom Zoom Controls
  ======================================================= */

  function changeZoom(
    amount
  ) {
    const container =
      scrollAreaRef.current;


    setZoom(
      (
        currentZoom
      ) => {
        const nextZoom =
          Math.min(
            MAX_ZOOM,

            Math.max(
              MIN_ZOOM,

              Number(
                (
                  currentZoom +
                  amount
                ).toFixed(
                  2
                )
              )
            )
          );


        if (
          container
        ) {
          const graphCenterX =
            (
              container.scrollLeft +
              container.clientWidth /
                2
            ) /
            currentZoom;


          const graphCenterY =
            (
              container.scrollTop +
              container.clientHeight /
                2
            ) /
            currentZoom;


          setTimeout(
            () => {
              container.scrollTo(
                {
                  left:
                    Math.max(
                      0,

                      graphCenterX *
                        nextZoom -
                        container.clientWidth /
                          2
                    ),

                  top:
                    Math.max(
                      0,

                      graphCenterY *
                        nextZoom -
                        container.clientHeight /
                          2
                    ),
                }
              );
            },
            0
          );
        }


        return nextZoom;
      }
    );
  }


  /* =======================================================
     Fit Full Graph
  ======================================================= */

  function fitAll() {
    const container =
      scrollAreaRef.current;


    if (
      !container
    ) {
      return;
    }


    const horizontalZoom =
      (
        container.clientWidth -
        40
      ) /
      canvas.width;


    const verticalZoom =
      (
        container.clientHeight -
        40
      ) /
      canvas.height;


    const nextZoom =
      Math.min(
        1,

        Math.max(
          MIN_ZOOM,

          Math.min(
            horizontalZoom,
            verticalZoom
          )
        )
      );


    setZoom(
      nextZoom
    );


    setTimeout(
      () => {
        const scaledWidth =
          canvas.width *
          nextZoom;


        const scaledHeight =
          canvas.height *
          nextZoom;


        container.scrollTo({
          left:
            Math.max(
              0,

              (
                scaledWidth -
                container.clientWidth
              ) /
                2
            ),

          top:
            Math.max(
              0,

              (
                scaledHeight -
                container.clientHeight
              ) /
                2
            ),

          behavior:
            "smooth",
        });
      },
      50
    );
  }


  /* =======================================================
     Graph Summary
  ======================================================= */

  const categories =
    useMemo(
      () => {
        const result = {
          upstream: 0,

          downstream: 0,

          datasets: 0,

          dashboards: 0,

          pipelines: 0,
        };


        (
          graph?.nodes ||
          []
        ).forEach(
          (node) => {
            if (
              node.direction ===
              "upstream"
            ) {
              result.upstream += 1;
            }


            if (
              node.direction ===
              "downstream"
            ) {
              result.downstream += 1;
            }


            if (
              node.category ===
              "dataset"
            ) {
              result.datasets += 1;
            }


            if (
              node.category ===
              "dashboard"
            ) {
              result.dashboards += 1;
            }


            if (
              node.category ===
              "pipeline"
            ) {
              result.pipelines += 1;
            }
          }
        );


        return result;
      },
      [
        graph,
      ]
    );


  /* =======================================================
     Selected Asset Name
  ======================================================= */

  const selectedAssetName =
    selectedNode
      ? getAssetDisplayName(
          selectedNode.name,
          selectedNode.id
        )
      : "";


  /* =======================================================
     UI
  ======================================================= */

  return (
    <article
      className={`panel ${styles.graphPanel}`}
    >
      {/* Header */}

      <div className={styles.header}>
        <div>
          <p className="eyebrow">
            DATAHUB CONTEXT GRAPH
          </p>

          <h3>
            Interactive Blast Radius
          </h3>

          <p className={styles.subtitle}>
            Explore the upstream and
            downstream relationships
            discovered from DataHub
            lineage.
          </p>
        </div>


        {graph && (
          <div
            className={
              styles.graphStats
            }
          >
            <span>
              <strong>
                {
                  graph.node_count
                }
              </strong>

              nodes
            </span>


            <span>
              <strong>
                {
                  graph.edge_count
                }
              </strong>

              relationships
            </span>
          </div>
        )}
      </div>


      {/* Legend */}

      <div className={styles.legend}>
        <span>
          <i
            className={
              styles.incidentDot
            }
          />

          Incident
        </span>


        <span>
          <i
            className={
              styles.datasetDot
            }
          />

          Dataset
        </span>


        <span>
          <i
            className={
              styles.pipelineDot
            }
          />

          Pipeline
        </span>


        <span>
          <i
            className={
              styles.dashboardDot
            }
          />

          Dashboard
        </span>
      </div>


      {/* Loading */}

      {loading && (
        <div
          className={
            styles.loadingState
          }
        >
          <div
            className={
              styles.loader
            }
          />

          <strong>
            Building DataHub
            lineage graph
          </strong>

          <span>
            Reading exact asset
            relationships...
          </span>
        </div>
      )}


      {/* Error */}

      {!loading &&
        error && (
          <div
            className={
              styles.errorState
            }
          >
            <strong>
              Lineage graph could
              not be loaded
            </strong>

            <span>
              {error}
            </span>
          </div>
        )}


      {/* Graph */}

      {!loading &&
        !error &&
        nodes.length > 0 && (
          <>
            {/* Top Controls */}

            <div
              className={
                styles.graphToolbar
              }
            >
              <div
                className={
                  styles.zoomControls
                }
              >
                <button
                  type="button"
                  onClick={() =>
                    changeZoom(
                      -0.1
                    )
                  }
                  disabled={
                    zoom <=
                    MIN_ZOOM
                  }
                >
                  −
                </button>


                <span>
                  {Math.round(
                    zoom *
                      100
                  )}
                  %
                </span>


                <button
                  type="button"
                  onClick={() =>
                    changeZoom(
                      0.1
                    )
                  }
                  disabled={
                    zoom >=
                    MAX_ZOOM
                  }
                >
                  +
                </button>
              </div>


              <div
                className={
                  styles.viewControls
                }
              >
                <button
                  type="button"
                  onClick={
                    fitAll
                  }
                >
                  Fit all
                </button>


                <button
                  type="button"
                  onClick={
                    centerIncident
                  }
                >
                  Center incident
                </button>
              </div>
            </div>


            <p
              className={
                styles.scrollHint
              }
            >
              Use the horizontal and
              vertical scrollbars to
              explore the full lineage
              graph.
            </p>


            {/* Scrollable Graph */}

            <div
              ref={
                scrollAreaRef
              }
              className={
                styles.scrollArea
              }
            >
              <div
                className={
                  styles.zoomSizer
                }
                style={{
                  width:
                    canvas.width *
                    zoom,

                  height:
                    canvas.height *
                    zoom,
                }}
              >
                <div
                  className={
                    styles.flowCanvas
                  }
                  style={{
                    width:
                      canvas.width,

                    height:
                      canvas.height,

                    transform:
                      `scale(${zoom})`,
                  }}
                >
                  <ReactFlow
                    nodes={
                      nodes
                    }
                    edges={
                      edges
                    }
                    nodeTypes={
                      nodeTypes
                    }
                    onNodesChange={
                      onNodesChange
                    }
                    onEdgesChange={
                      onEdgesChange
                    }
                    onNodeClick={(
                      event,
                      node
                    ) =>
                      setSelectedNode(
                        node.data
                      )
                    }
                    defaultViewport={{
                      x: 0,
                      y: 0,
                      zoom: 1,
                    }}
                    minZoom={
                      0.25
                    }
                    maxZoom={
                      2
                    }
                    fitView={
                      false
                    }
                    nodesConnectable={
                      false
                    }
                    nodesDraggable
                    panOnDrag={
                      false
                    }
                    panOnScroll={
                      false
                    }
                    zoomOnScroll={
                      false
                    }
                    zoomOnDoubleClick={
                      false
                    }
                    preventScrolling={
                      false
                    }
                    deleteKeyCode={
                      null
                    }
                    colorMode="dark"
                  >
                    <Background
                      gap={20}
                      size={1}
                    />

                    {/* React Flow zoom controls */}

                    <Controls
                      position="bottom-left"
                      showInteractive={
                        false
                      }
                    />

                    {/* Mini Map */}

                    <MiniMap
                      position="bottom-right"
                      pannable
                      zoomable
                    />
                  </ReactFlow>
                </div>
              </div>
            </div>


            {/* Graph Summary */}

            <div
              className={
                styles.summaryGrid
              }
            >
              <div>
                <strong>
                  {
                    categories.upstream
                  }
                </strong>

                <span>
                  Upstream
                </span>
              </div>


              <div>
                <strong>
                  {
                    categories.downstream
                  }
                </strong>

                <span>
                  Downstream
                </span>
              </div>


              <div>
                <strong>
                  {
                    categories.datasets
                  }
                </strong>

                <span>
                  Datasets
                </span>
              </div>


              <div>
                <strong>
                  {
                    categories.dashboards
                  }
                </strong>

                <span>
                  Dashboards
                </span>
              </div>


              <div>
                <strong>
                  {
                    categories.pipelines
                  }
                </strong>

                <span>
                  Pipelines
                </span>
              </div>
            </div>


            {/* Selected Asset Details */}

            {selectedNode && (
              <div
                className={
                  styles.selectedAsset
                }
              >
                <div>
                  <span
                    className={
                      styles.selectedLabel
                    }
                  >
                    SELECTED ASSET
                  </span>

                  <strong>
                    {
                      selectedAssetName
                    }
                  </strong>
                </div>


                <div
                  className={
                    styles.selectedMeta
                  }
                >
                  <span>
                    Type

                    <strong>
                      {selectedNode
                        .asset_type ||
                        "Unknown"}
                    </strong>
                  </span>


                  <span>
                    Platform

                    <strong>
                      {selectedNode
                        .platform ||
                        "Unknown"}
                    </strong>
                  </span>


                  <span>
                    Direction

                    <strong>
                      {selectedNode
                        .is_incident_source
                        ? "Incident Source"
                        : selectedNode
                            .direction ||
                          "Unknown"}
                    </strong>
                  </span>


                  <span>
                    Distance

                    <strong>
                      {
                        selectedNode.hops
                      }{" "}
                      hops
                    </strong>
                  </span>
                </div>


                {selectedNode
                  .domain && (
                  <p>
                    Business domain:{" "}

                    <strong>
                      {
                        selectedNode.domain
                      }
                    </strong>
                  </p>
                )}


                {selectedNode
                  .owners
                  ?.length >
                  0 && (
                  <p>
                    Owners:{" "}

                    <strong>
                      {selectedNode.owners.join(
                        ", "
                      )}
                    </strong>
                  </p>
                )}


                <button
                  type="button"
                  onClick={() =>
                    setSelectedNode(
                      null
                    )
                  }
                  aria-label="Close selected asset"
                >
                  ×
                </button>
              </div>
            )}
          </>
        )}


      {/* Empty */}

      {!loading &&
        !error &&
        nodes.length === 0 && (
          <div
            className={
              styles.emptyState
            }
          >
            No lineage relationships
            were found for this
            incident.
          </div>
        )}
    </article>
  );
}