"use client";

import { useEffect, useMemo, useState } from "react";
import GraphCanvas from "@/components/GraphCanvas";
import { graphSummary, graphUserSummary, userImpact } from "@/lib/api";

function formatTime(timestampSeconds) {
  if (!timestampSeconds) return "-";
  return new Date(Number(timestampSeconds) * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function GraphPanel({ userId, refreshSignal = 0 }) {
  const [mode, setMode] = useState("visual");
  const [impact, setImpact] = useState(null);
  const [main, setMain] = useState(null);
  const [personal, setPersonal] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      if (!userId) return;
      setLoading(true);
      setError("");
      try {
        const [impactData, mainSummary, personalSummary] = await Promise.all([
          userImpact(userId, 30),
          graphUserSummary({ userId, nodeLimit: 50, edgeLimit: 100 }),
          graphSummary({ scope: "personal", userId, nodeLimit: 50, edgeLimit: 100, minStrength: 0.01 }),
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
    return () => { cancelled = true; };
  }, [userId, refreshSignal]);

  const personalItems = impact?.personal_memory?.items || [];
  const mainItems = impact?.main_graph_impact?.items || [];

  return (
    <div className="graph-panel">
      <div className="panel-mode-switch mono" style={{padding:'0 20px', marginBottom:'16px'}}>
        <button
          className={mode === "visual" ? "active" : ""}
          onClick={() => setMode("visual")}
        >
          Visual
        </button>
        <button
          className={mode === "history" ? "active" : ""}
          onClick={() => setMode("history")}
        >
          History
        </button>
      </div>

      {error && <div className="panel-error mono">{error}</div>}

      {mode === "visual" ? (
        <div style={{display:'grid', gap:'20px', padding:'0 12px'}}>
          <GraphCanvas
            title="Active Main Clusters"
            summary={main}
            nodeLimit={20}
            edgeLimit={40}
            showLabels="hover"
          />
          <GraphCanvas
            title="Private State"
            summary={personal}
            nodeLimit={15}
            edgeLimit={30}
            showLabels="hover"
          />
        </div>
      ) : (
        <div className="contrib-list" style={{padding:'0 12px'}}>
          <h4 className="mono" style={{fontSize:'10px', color:'var(--muted)', marginBottom:'8px'}}>WORLD CONTRIBUTIONS</h4>
          {mainItems.map((item) => (
            <div key={item.record_id} className="contrib-row mono" style={{fontSize:'11px'}}>
              <div style={{fontWeight:'bold', color:'var(--secondary)'}}>{item.query}</div>
              <div style={{display:'flex', justifyContent:'space-between', marginTop:'4px', opacity:0.7}}>
                <span>+{item.credits_awarded} CR</span>
                <span>{formatTime(item.stored_at)}</span>
              </div>
            </div>
          ))}
          {mainItems.length === 0 && <div className="mono" style={{fontSize:'11px', opacity:0.5}}>No contributions yet.</div>}
          
          <h4 className="mono" style={{fontSize:'10px', color:'var(--muted)', marginTop:'20px', marginBottom:'8px'}}>PERSONAL FACTS</h4>
          {personalItems.map((item, i) => (
            <div key={i} className="contrib-row mono" style={{fontSize:'11px'}}>
              <div style={{color:'var(--muted)'}}>{item.attribute_value}</div>
              <div style={{textAlign:'right', marginTop:'4px', opacity:0.7}}>{formatTime(item.stored_at)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
