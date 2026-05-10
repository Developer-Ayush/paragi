"use client";

import { useEffect, useMemo, useState } from "react";
import GraphCanvas from "@/components/GraphCanvas";
import { graphSummary, graphUserSummary, userImpact } from "@/lib/api";

function formatTime(timestampSeconds) {
  if (!timestampSeconds) return "-";
  return new Date(Number(timestampSeconds) * 1000).toLocaleString();
}

export default function GraphPanel({ userId, refreshSignal = 0 }) {
  const [mode, setMode] = useState("contrib");
  const [impact, setImpact] = useState(null);
  const [main, setMain] = useState(null);
  const [personal, setPersonal] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showMain, setShowMain] = useState(true);
  const [showPersonal, setShowPersonal] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      if (!userId) return;
      setLoading(true);
      setError("");
      try {
        const [impactData, mainSummary, personalSummary] = await Promise.all([
          userImpact(userId, 30),
          graphUserSummary({ userId, nodeLimit: 70, edgeLimit: 120 }),
          graphSummary({ scope: "personal", userId, nodeLimit: 70, edgeLimit: 120, minStrength: 0.01 }),
        ]);
        if (cancelled) return;
        setImpact(impactData);
        setMain(mainSummary);
        setPersonal(personalSummary);
      } catch (err) {
        if (cancelled) return;
        setError(err.message || "Failed to load contribution data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [userId, refreshSignal]);

  const summary = impact?.summary || {};
  const personalItems = impact?.personal_memory?.items || [];
  const mainItems = impact?.main_graph_impact?.items || [];

  const statRows = useMemo(() => {
    return [
      ["Main impact records", summary.main_impact_records || 0],
      ["Personal records", summary.personal_records || 0],
      ["Nodes you added to main", summary.nodes_added_to_main_graph || 0],
      ["Edges you added to main", summary.edges_added_to_main_graph || 0],
      ["Credits earned", summary.credits_earned_from_impact || 0],
    ];
  }, [summary]);

  return (
    <div className="graph-panel">
      <div className="graph-top-meta">
        <strong style={{ color: 'var(--accent)', fontSize: '14px', letterSpacing: '0.05em' }}>KNOWLEDGE PANEL</strong>
        <span style={{ color: 'var(--muted)', fontSize: '11px' }}>{loading ? "refreshing..." : `user: ${userId}`}</span>
      </div>

      {error && <div className="panel-error">{error}</div>}

      <div className="panel-mode-switch">
        <button
          type="button"
          className={mode === "contrib" ? "active" : ""}
          onClick={() => setMode("contrib")}
        >
          Contributions
        </button>
        <button
          type="button"
          className={mode === "visual" ? "active" : ""}
          onClick={() => setMode("visual")}
        >
          Graph Visual
        </button>
      </div>

      <section className="impact-card">
        <h4>Contribution Summary</h4>
        <div className="impact-grid">
          {statRows.map(([label, value]) => (
            <div key={label} className="impact-row">
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      </section>

      {mode === "contrib" ? (
        <>
          <section className="contrib-card">
            <header className="contrib-head">
              <strong>Main Graph Contributions</strong>
              <button type="button" onClick={() => setShowMain((value) => !value)}>
                {showMain ? "Collapse" : "Expand"}
              </button>
            </header>
            {showMain && (
              <div className="contrib-list">
                {mainItems.length === 0 && <div className="contrib-empty">No main-graph contributions yet.</div>}
                {mainItems.map((item) => (
                  <article key={item.record_id} className="contrib-row">
                    <div className="contrib-title">{item.query}</div>
                    <small>
                      nodes={item.new_nodes_created} | edges={item.created_edges} | credits={item.credits_awarded}
                    </small>
                    <small>{item.domain} | {formatTime(item.stored_at)}</small>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="contrib-card">
            <header className="contrib-head">
              <strong>Personal Graph Contributions</strong>
              <button type="button" onClick={() => setShowPersonal((value) => !value)}>
                {showPersonal ? "Collapse" : "Expand"}
              </button>
            </header>
            {showPersonal && (
              <div className="contrib-list">
                {personalItems.length === 0 && <div className="contrib-empty">No personal memory stored yet.</div>}
                {personalItems.map((item, index) => (
                  <article key={`${item.attribute_value}_${item.stored_at}_${index}`} className="contrib-row">
                    <div className="contrib-title">{item.attribute_value}</div>
                    <small>confidence={Number(item.confidence || 0).toFixed(3)}</small>
                    <small>{formatTime(item.stored_at)}</small>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      ) : (
        <>
          <GraphCanvas
            title="Your Main Graph Contributions"
            summary={main}
            nodeLimit={24}
            edgeLimit={52}
            showLabels="hover"
          />
          <GraphCanvas
            title="Personal Graph Visual"
            summary={personal}
            nodeLimit={22}
            edgeLimit={46}
            showLabels="hover"
          />
        </>
      )}
    </div>
  );
}
