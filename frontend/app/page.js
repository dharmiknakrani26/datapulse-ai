"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import LineageGraph from "./components/LineageGraph";
import IncidentEvidence from "./components/IncidentEvidence";
import DataSourceInfo from "./components/DataSourceInfo";

import {
  cleanTechnicalText,
  extractAssetName,
  formatIncidentType,
} from "./utils/assetDisplay";


const API_BASE =
  "http://localhost:8000";


const NAV_ITEMS = [
  {
    id: "command",
    label: "Command Center",
  },
  {
    id: "incidents",
    label: "Incident Memory",
  },
];


/* =========================================================
   Helpers
========================================================= */

function formatDate(value) {
  if (!value) {
    return "—";
  }

  try {
    return new Date(
      value
    ).toLocaleString();
  } catch {
    return value;
  }
}


function riskClass(level) {
  return String(
    level || "low"
  ).toLowerCase();
}


function statusClass(status) {
  return String(
    status || "open"
  ).toLowerCase();
}


function isResolved(status) {
  return (
    String(
      status || ""
    ).toLowerCase() ===
    "resolved"
  );
}


function shortUrn(urn) {
  return extractAssetName(
    urn
  );
}


/* =========================================================
   Investigation Loading State
========================================================= */

function LoadingState() {
  const stages = [
    "Reading DataHub context graph",
    "Tracing upstream and downstream lineage",
    "Calculating business impact",
    "Running incident analysis",
    "Writing intelligence back to DataHub",
  ];


  return (
    <div className="loading-panel">
      <div className="pulse-loader">
        <span />
        <span />
        <span />
      </div>


      <div>
        <h3>
          DataPulse is investigating
        </h3>

        <p>
          The workflow is analyzing
          the incident and connected
          data assets.
        </p>


        <div className="loading-stages">
          {stages.map(
            (
              stage,
              index
            ) => (
              <div
                className="loading-stage"
                key={stage}
              >
                <span className="stage-number">
                  {index + 1}
                </span>

                <span>
                  {stage}
                </span>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}


/* =========================================================
   Main Application
========================================================= */

export default function Home() {
  const [
    view,
    setView,
  ] = useState(
    "command"
  );


  const [
    systemStatus,
    setSystemStatus,
  ] = useState(
    null
  );


  const [
    incidents,
    setIncidents,
  ] = useState(
    []
  );


  const [
    activeIncident,
    setActiveIncident,
  ] = useState(
    null
  );


  const [
    loading,
    setLoading,
  ] = useState(
    false
  );


  const [
    resolving,
    setResolving,
  ] = useState(
    false
  );


  const [
    error,
    setError,
  ] = useState(
    ""
  );


  const [
    form,
    setForm,
  ] = useState({
    search_query:
      "orders",

    incident_type:
      "freshness",

    max_hops: 3,
  });


  /* =======================================================
     Load System Status
  ======================================================= */

  const loadSystemStatus =
    useCallback(
      async () => {
        try {
          const response =
            await fetch(
              `${API_BASE}/api/system/status`
            );


          const data =
            await response.json();


          setSystemStatus(
            data
          );
        } catch {
          setSystemStatus({
            datapulse_api:
              "offline",

            datahub: {
              connected:
                false,
            },

            ai: {
              api_key_configured:
                false,
            },
          });
        }
      },

      []
    );


  /* =======================================================
     Load Incident History

     Priority:
     1. Newest unresolved incident
     2. Newest resolved incident
  ======================================================= */

  const loadIncidents =
    useCallback(
      async (
        selectPreferred =
          false
      ) => {
        try {
          const response =
            await fetch(
              `${API_BASE}/api/incidents`
            );


          if (
            !response.ok
          ) {
            throw new Error(
              "Could not load incident history."
            );
          }


          const data =
            await response.json();


          const records =
            data.incidents ||
            [];


          setIncidents(
            records
          );


          if (
            selectPreferred &&
            records.length > 0
          ) {
            const newestActive =
              records.find(
                (
                  record
                ) =>
                  !isResolved(
                    record
                      ?.incident
                      ?.status
                  )
              );


            setActiveIncident(
              newestActive ||
                records[0]
            );
          }
        } catch (
          requestError
        ) {
          console.error(
            requestError
          );
        }
      },

      []
    );


  /* =======================================================
     Initial Load
  ======================================================= */

  useEffect(() => {
    loadSystemStatus();

    loadIncidents(
      true
    );
  }, [
    loadSystemStatus,
    loadIncidents,
  ]);


  /* =======================================================
     Run Investigation
  ======================================================= */

  async function runInvestigation(
    event
  ) {
    event.preventDefault();


    setLoading(
      true
    );


    setError(
      ""
    );


    try {
      const response =
        await fetch(
          `${API_BASE}/api/incidents/analyze`,

          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                asset_urn:
                  null,

                search_query:
                  form.search_query,

                incident_type:
                  form.incident_type,

                max_hops:
                  Number(
                    form.max_hops
                  ),
              }),
          }
        );


      const data =
        await response.json();


      if (
        !response.ok
      ) {
        throw new Error(
          data.detail ||
            "Incident investigation failed."
        );
      }


      setActiveIncident(
        data.result
      );


      await loadIncidents();


      setView(
        "command"
      );
    } catch (
      requestError
    ) {
      setError(
        requestError.message ||
          "Something went wrong."
      );
    } finally {
      setLoading(
        false
      );
    }
  }


  /* =======================================================
     Resolve Incident
  ======================================================= */

  async function resolveIncident() {
    const incidentId =
      activeIncident
        ?.incident
        ?.incident_id;


    if (!incidentId) {
      return;
    }


    setResolving(
      true
    );


    setError(
      ""
    );


    try {
      const response =
        await fetch(
          `${API_BASE}/api/incidents/${incidentId}/resolve`,

          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                issue_cleared:
                  true,

                signal_source:
                  "DataPulse Demo Monitor",

                details:
                  "The monitoring system reports that the original incident condition has cleared.",

                verification_mode:
                  "simulated_demo",
              }),
          }
        );


      const data =
        await response.json();


      if (
        !response.ok
      ) {
        throw new Error(
          data.detail ||
            "Resolution verification failed."
        );
      }


      setActiveIncident(
        data.result
      );


      await loadIncidents();
    } catch (
      requestError
    ) {
      setError(
        requestError.message ||
          "Resolution failed."
      );
    } finally {
      setResolving(
        false
      );
    }
  }


  /* =======================================================
     Selected Incident
  ======================================================= */

  const incident =
    activeIncident
      ?.incident;


  const investigation =
    activeIncident
      ?.investigation;


  const impact =
    activeIncident
      ?.impact;


  const commander =
    activeIncident
      ?.commander_analysis;


  const verification =
    activeIncident
      ?.resolution_verification;


  const selectedIncidentResolved =
    isResolved(
      incident?.status
    );


  const incidentSectionLabel =
    selectedIncidentResolved
      ? "RESOLVED INCIDENT"
      : "CURRENT INCIDENT";


  /* =======================================================
     Dashboard Metrics
  ======================================================= */

  const activeRecords =
    useMemo(
      () =>
        incidents.filter(
          (
            record
          ) =>
            !isResolved(
              record
                ?.incident
                ?.status
            )
        ),

      [
        incidents,
      ]
    );


  const resolvedRecords =
    useMemo(
      () =>
        incidents.filter(
          (
            record
          ) =>
            isResolved(
              record
                ?.incident
                ?.status
            )
        ),

      [
        incidents,
      ]
    );


  const activeCount =
    activeRecords.length;


  const resolvedCount =
    resolvedRecords.length;


  const highestRisk =
    useMemo(
      () =>
        incidents.reduce(
          (
            highest,
            record
          ) =>
            Math.max(
              highest,

              Number(
                record
                  ?.impact
                  ?.score ||
                  0
              )
            ),

          0
        ),

      [
        incidents,
      ]
    );


  const activeRiskRecord =
    activeRecords[0];


  const assetsAtRisk =
    Number(
      activeRiskRecord
        ?.investigation
        ?.total_downstream ||
        0
    );


  /* =======================================================
     UI
  ======================================================= */

  return (
    <div className="app-shell">
      {/* =================================================
          Sidebar
      ================================================= */}

      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <span />
            <span />
            <span />
          </div>


          <div>
            <h1>
              DataPulse
            </h1>
          </div>
        </div>


        <nav className="nav-list">
          {NAV_ITEMS.map(
            (
              item
            ) => (
              <button
                key={
                  item.id
                }
                type="button"
                className={
                  view ===
                  item.id
                    ? "nav-item active"
                    : "nav-item"
                }
                onClick={() =>
                  setView(
                    item.id
                  )
                }
              >
                {
                  item.label
                }
              </button>
            )
          )}
        </nav>


        <div className="sidebar-status">
          <p className="eyebrow">
            SYSTEM STATUS
          </p>


          <div className="status-line">
            <span
              className={
                systemStatus
                  ?.datahub
                  ?.connected
                  ? "status-dot online"
                  : "status-dot offline"
              }
            />

            <span>
              DataHub{" "}

              {systemStatus
                ?.datahub
                ?.connected
                ? "Connected"
                : "Offline"}
            </span>
          </div>


          <div className="status-line">
            <span
              className={
                systemStatus
                  ?.ai
                  ?.api_key_configured
                  ? "status-dot online"
                  : "status-dot offline"
              }
            />

            <span>
              Analysis{" "}

              {systemStatus
                ?.ai
                ?.api_key_configured
                ? "Ready"
                : "Unavailable"}
            </span>
          </div>
        </div>
      </aside>


      {/* =================================================
          Main Content
      ================================================= */}

      <main className="main-content">
        {/* Top Bar */}

        <header className="topbar">
          <div>
            <p className="eyebrow">
              INCIDENT RESPONSE
            </p>

            <h2>
              {view ===
              "command"
                ? "Command Center"
                : "Incident Memory"}
            </h2>
          </div>


          <div className="topbar-actions">
            <div className="live-pill">
              <span className="status-dot online" />

              Live
            </div>


            <a
              href="http://localhost:9002"
              target="_blank"
              rel="noreferrer"
              className="secondary-button"
            >
              Open DataHub
            </a>
          </div>
        </header>


        {/* Error Banner */}

        {error && (
          <div className="error-banner">
            <strong>
              Investigation error
            </strong>

            <span>
              {error}
            </span>

            <button
              type="button"
              onClick={() =>
                setError(
                  ""
                )
              }
            >
              ×
            </button>
          </div>
        )}


        {/* =================================================
            Command Center
        ================================================= */}

        {view ===
          "command" && (
          <>
            {/* Dashboard Metrics */}

            <section className="metric-grid">
              <article className="metric-card">
                <div>
                  <span>
                    Active Incidents
                  </span>

                  <strong>
                    {
                      activeCount
                    }
                  </strong>
                </div>
              </article>


              <article className="metric-card">
                <div>
                  <span>
                    Highest Impact
                  </span>

                  <strong>
                    {
                      highestRisk
                    }

                    <small>
                      /100
                    </small>
                  </strong>
                </div>
              </article>


              <article className="metric-card">
                <div>
                  <span>
                    Assets at Risk
                  </span>

                  <strong>
                    {
                      assetsAtRisk
                    }
                  </strong>
                </div>
              </article>


              <article className="metric-card">
                <div>
                  <span>
                    Resolved
                  </span>

                  <strong>
                    {
                      resolvedCount
                    }
                  </strong>
                </div>
              </article>
            </section>


            {/* Workspace */}

            <section className="workspace-grid">
              {/* =========================================
                  Main Column
              ========================================= */}

              <div className="workspace-main">
                {/* New Investigation */}

                <article className="panel new-incident-panel">
                  <div className="panel-header">
                    <div>
                      <p className="eyebrow">
                        NEW INVESTIGATION
                      </p>

                      <h3>
                        Launch investigation
                      </h3>
                    </div>
                  </div>


                  <DataSourceInfo />


                  <form
                    className="incident-form"
                    onSubmit={
                      runInvestigation
                    }
                  >
                    <label>
                      <span>
                        Dataset search
                      </span>

                      <input
                        value={
                          form.search_query
                        }
                        onChange={(
                          event
                        ) =>
                          setForm({
                            ...form,

                            search_query:
                              event
                                .target
                                .value,
                          })
                        }
                        placeholder="orders"
                      />
                    </label>


                    <label>
                      <span>
                        Incident type
                      </span>

                      <select
                        value={
                          form.incident_type
                        }
                        onChange={(
                          event
                        ) =>
                          setForm({
                            ...form,

                            incident_type:
                              event
                                .target
                                .value,
                          })
                        }
                      >
                        <option value="freshness">
                          Freshness failure
                        </option>

                        <option value="data_quality">
                          Data quality failure
                        </option>

                        <option value="schema_change">
                          Schema change
                        </option>
                      </select>
                    </label>


                    <label>
                      <span>
                        Lineage depth
                      </span>

                      <select
                        value={
                          form.max_hops
                        }
                        onChange={(
                          event
                        ) =>
                          setForm({
                            ...form,

                            max_hops:
                              event
                                .target
                                .value,
                          })
                        }
                      >
                        <option value={1}>
                          1 hop
                        </option>

                        <option value={2}>
                          2 hops
                        </option>

                        <option value={3}>
                          3 hops
                        </option>

                        <option value={4}>
                          4 hops
                        </option>

                        <option value={5}>
                          5 hops
                        </option>
                      </select>
                    </label>


                    <button
                      type="submit"
                      className="primary-button"
                      disabled={
                        loading
                      }
                    >
                      {loading
                        ? "Investigating..."
                        : "Run Investigation"}
                    </button>
                  </form>
                </article>


                {/* Investigation Content */}

                {loading ? (
                  <LoadingState />
                ) : activeIncident ? (
                  <>
                    {/* Incident Overview */}

                    <article className="panel incident-overview">
                      <div className="panel-header">
                        <div>
                          <p className="eyebrow">
                            {
                              incidentSectionLabel
                            }
                          </p>

                          <h3>
                            {
                              incident
                                ?.title
                            }
                          </h3>
                        </div>


                        <span
                          className={`status-badge ${statusClass(
                            incident
                              ?.status
                          )}`}
                        >
                          {
                            incident
                              ?.status
                          }
                        </span>
                      </div>


                      <div className="incident-meta">
                        <div>
                          <span>
                            Incident ID
                          </span>

                          <strong>
                            {
                              incident
                                ?.incident_id
                            }
                          </strong>
                        </div>


                        <div>
                          <span>
                            Asset
                          </span>

                          <strong
                            title={
                              incident
                                ?.asset_urn
                            }
                          >
                            {shortUrn(
                              incident
                                ?.asset_urn
                            )}
                          </strong>
                        </div>


                        <div>
                          <span>
                            Created
                          </span>

                          <strong>
                            {formatDate(
                              incident
                                ?.created_at
                            )}
                          </strong>
                        </div>
                      </div>
                    </article>


                    {/* Lineage Graph */}

                    {incident
                      ?.incident_id && (
                      <LineageGraph
                        incidentId={
                          incident
                            .incident_id
                        }
                      />
                    )}


                    {/* Incident Analysis */}

                    <article className="panel">
                      <div className="panel-header">
                        <div>
                          <p className="eyebrow">
                            INCIDENT ANALYSIS
                          </p>

                          <h3>
                            Executive analysis
                          </h3>
                        </div>
                      </div>


                      <div className="commander-section">
                        <h4>
                          What happened?
                        </h4>

                        <p>
                          {cleanTechnicalText(
                            commander
                              ?.executive_summary
                          )}
                        </p>
                      </div>


                      <div className="commander-section">
                        <h4>
                          Business impact
                        </h4>

                        <p>
                          {cleanTechnicalText(
                            commander
                              ?.business_impact_summary
                          )}
                        </p>
                      </div>


                      <div className="commander-section hypothesis">
                        <div className="section-title-row">
                          <h4>
                            Root-cause hypothesis
                          </h4>

                          <span>
                            {commander
                              ?.root_cause_confidence ||
                              0}
                            % confidence
                          </span>
                        </div>


                        <p>
                          {cleanTechnicalText(
                            commander
                              ?.root_cause_hypothesis
                          )}
                        </p>
                      </div>
                    </article>


                    {/* Evidence */}

                    <IncidentEvidence
                      evidence={
                        commander
                          ?.evidence ||
                        []
                      }
                      limitations={
                        commander
                          ?.limitations ||
                        []
                      }
                    />


                    {/* Recommended Actions */}

                    <article className="panel">
                      <div className="panel-header">
                        <div>
                          <p className="eyebrow">
                            RESPONSE PLAN
                          </p>

                          <h3>
                            Recommended actions
                          </h3>
                        </div>
                      </div>


                      <div className="action-list">
                        {(
                          commander
                            ?.recommended_actions ||
                          []
                        )
                          .slice()
                          .sort(
                            (
                              a,
                              b
                            ) =>
                              a.priority -
                              b.priority
                          )
                          .map(
                            (
                              action,
                              index
                            ) => (
                              <div
                                className="action-item"
                                key={`${action.priority}-${index}`}
                              >
                                <div className="action-priority">
                                  {
                                    action.priority
                                  }
                                </div>


                                <div>
                                  <strong>
                                    {cleanTechnicalText(
                                      action.action
                                    )}
                                  </strong>

                                  <p>
                                    {cleanTechnicalText(
                                      action.reason
                                    )}
                                  </p>
                                </div>
                              </div>
                            )
                          )}
                      </div>
                    </article>
                  </>
                ) : (
                  <article className="panel empty-state">
                    <h3>
                      No investigation selected
                    </h3>

                    <p>
                      Start an investigation
                      above to analyze the
                      DataHub context graph.
                    </p>
                  </article>
                )}
              </div>


              {/* =========================================
                  Right Column
              ========================================= */}

              <aside className="workspace-side">
                {/* Impact Score */}

                <article className="panel impact-panel">
                  <p className="eyebrow">
                    DATAPULSE IMPACT SCORE
                  </p>


                  <div
                    className={`score-ring ${riskClass(
                      impact
                        ?.risk_level
                    )}`}
                    style={{
                      "--score":
                        impact
                          ?.score ||
                        0,
                    }}
                  >
                    <div>
                      <strong>
                        {impact
                          ?.score ||
                          0}
                      </strong>

                      <span>
                        /100
                      </span>
                    </div>
                  </div>


                  <span
                    className={`risk-badge ${riskClass(
                      impact
                        ?.risk_level
                    )}`}
                  >
                    {impact
                      ?.risk_level ||
                      "NO RISK"}
                  </span>


                  <p className="score-description">
                    {cleanTechnicalText(
                      impact
                        ?.explanation ||
                        "Run an investigation to calculate business impact."
                    )}
                  </p>
                </article>


                {/* Blast Radius */}

                <article className="panel">
                  <div className="panel-header compact">
                    <div>
                      <p className="eyebrow">
                        BLAST RADIUS
                      </p>

                      <h3>
                        Affected context
                      </h3>
                    </div>
                  </div>


                  <div className="blast-grid">
                    <div>
                      <strong>
                        {investigation
                          ?.total_downstream ||
                          0}
                      </strong>

                      <span>
                        Downstream
                      </span>
                    </div>


                    <div>
                      <strong>
                        {investigation
                          ?.affected_dashboards ||
                          0}
                      </strong>

                      <span>
                        Dashboards
                      </span>
                    </div>


                    <div>
                      <strong>
                        {investigation
                          ?.affected_datasets ||
                          0}
                      </strong>

                      <span>
                        Datasets
                      </span>
                    </div>


                    <div>
                      <strong>
                        {investigation
                          ?.affected_domains
                          ?.length ||
                          0}
                      </strong>

                      <span>
                        Domains
                      </span>
                    </div>
                  </div>


                  <div className="tag-section">
                    <span className="small-label">
                      BUSINESS DOMAINS
                    </span>


                    <div className="tag-list">
                      {investigation
                        ?.affected_domains
                        ?.length ? (
                        investigation
                          .affected_domains
                          .map(
                            (
                              domain
                            ) => (
                              <span
                                className="context-tag"
                                key={
                                  domain
                                }
                              >
                                {
                                  domain
                                }
                              </span>
                            )
                          )
                      ) : (
                        <span className="muted">
                          No domains detected
                        </span>
                      )}
                    </div>
                  </div>
                </article>


                {/* Verify Resolution */}

                {incident &&
                  !selectedIncidentResolved && (
                    <article className="panel resolution-panel">
                      <p className="eyebrow">
                        RESOLUTION
                      </p>

                      <h3>
                        Verify recovery
                      </h3>

                      <p>
                        Verify that the
                        incident condition
                        has cleared and the
                        source asset remains
                        accessible.
                      </p>

                      <button
                        type="button"
                        className="resolve-button"
                        disabled={
                          resolving
                        }
                        onClick={
                          resolveIncident
                        }
                      >
                        {resolving
                          ? "Verifying..."
                          : "Verify Resolution"}
                      </button>
                    </article>
                  )}


                {/* Resolved */}

                {verification
                  ?.verified && (
                  <article className="panel resolved-panel">
                    <div className="resolved-check">
                      ✓
                    </div>

                    <h3>
                      Resolution verified
                    </h3>

                    <p>
                      {cleanTechnicalText(
                        verification
                          .message
                      )}
                    </p>
                  </article>
                )}
              </aside>
            </section>
          </>
        )}


        {/* =================================================
            Incident Memory
        ================================================= */}

        {view ===
          "incidents" && (
          <section className="history-layout">
            <article className="panel history-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">
                    INCIDENT HISTORY
                  </p>

                  <h3>
                    Previous investigations
                  </h3>
                </div>


                <span className="count-badge">
                  {
                    incidents.length
                  }{" "}
                  records
                </span>
              </div>


              {incidents.length ? (
                <div className="incident-table">
                  <div className="table-row table-head">
                    <span>
                      Incident
                    </span>

                    <span>
                      Type
                    </span>

                    <span>
                      Impact
                    </span>

                    <span>
                      Status
                    </span>

                    <span>
                      Created
                    </span>
                  </div>


                  {incidents.map(
                    (
                      record
                    ) => (
                      <button
                        type="button"
                        className="table-row"
                        key={
                          record
                            .incident
                            .incident_id
                        }
                        onClick={() => {
                          setActiveIncident(
                            record
                          );

                          setView(
                            "command"
                          );
                        }}
                      >
                        <span>
                          <strong>
                            {
                              record
                                .incident
                                .incident_id
                            }
                          </strong>

                          <small>
                            {shortUrn(
                              record
                                .incident
                                .asset_urn
                            )}
                          </small>
                        </span>


                        <span>
                          {formatIncidentType(
                            record
                              .incident
                              .incident_type
                          )}
                        </span>


                        <span>
                          <strong>
                            {
                              record
                                .impact
                                .score
                            }
                            /100
                          </strong>
                        </span>


                        <span>
                          <span
                            className={`status-badge ${statusClass(
                              record
                                .incident
                                .status
                            )}`}
                          >
                            {
                              record
                                .incident
                                .status
                            }
                          </span>
                        </span>


                        <span>
                          {formatDate(
                            record
                              .incident
                              .created_at
                          )}
                        </span>
                      </button>
                    )
                  )}
                </div>
              ) : (
                <div className="empty-state">
                  <h3>
                    No incident history
                  </h3>

                  <p>
                    Completed investigations
                    will appear here.
                  </p>
                </div>
              )}
            </article>
          </section>
        )}
      </main>
    </div>
  );
}