"use client";

import { useMemo, useState } from "react";

const WIDTH = 540;
const HEIGHT = 240;
const PAD = 20;

function shorten(label, size = 16) {
  if (!label) return "";
  return label.length > size ? `${label.slice(0, size)}...` : label;
}

function hashText(value) {
  let hash = 2166136261;
  for (let idx = 0; idx < value.length; idx += 1) {
    hash ^= value.charCodeAt(idx);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function buildPositions(nodes, edges) {
  const positions = {};
  const neighborMap = {};
  nodes.forEach(n => neighborMap[n.id] = new Set());
  edges.forEach(e => {
    if (!neighborMap[e.source_id] || !neighborMap[e.target_id]) return;
    neighborMap[e.source_id].add(e.target_id);
    neighborMap[e.target_id].add(e.source_id);
  });
  nodes.forEach((node, index) => {
    const seedX = hashText(`${node.id}:${index}`);
    const seedY = hashText(`${index}:${node.id}`);
    positions[node.id] = {
      x: PAD + (seedX % (WIDTH - PAD * 2)),
      y: PAD + (seedY % (HEIGHT - PAD * 2)),
    };
  });
  for (let step = 0; step < 80; step++) {
    nodes.forEach((nodeA) => {
      const a = positions[nodeA.id];
      let fx = 0, fy = 0;
      nodes.forEach((nodeB) => {
        if (nodeA.id === nodeB.id) return;
        const b = positions[nodeB.id];
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.hypot(dx, dy) || 0.1;
        if (dist < 35) {
          fx += (dx / dist) * (35 - dist) * 0.1;
          fy += (dy / dist) * (35 - dist) * 0.1;
        }
      });
      (neighborMap[nodeA.id] || []).forEach(nid => {
        const b = positions[nid];
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.hypot(dx, dy) || 0.1;
        const pull = (dist - 70) * 0.005;
        fx += (dx / dist) * pull; fy += (dy / dist) * pull;
      });
      a.x = Math.max(PAD, Math.min(WIDTH - PAD, a.x + fx));
      a.y = Math.max(PAD, Math.min(HEIGHT - PAD, a.y + fy));
    });
  }
  return positions;
}

export default function GraphCanvas({ title, summary, nodeLimit = 20 }) {
  const [hovered, setHovered] = useState(null);

  const { nodes, edges, positions } = useMemo(() => {
    const selectedNodes = (summary?.nodes || []).slice(0, nodeLimit);
    const nodeSet = new Set(selectedNodes.map(n => n.id));
    const selectedEdges = (summary?.edges || []).filter(e => nodeSet.has(e.source_id) && nodeSet.has(e.target_id));
    return { nodes: selectedNodes, edges: selectedEdges, positions: buildPositions(selectedNodes, selectedEdges) };
  }, [summary, nodeLimit]);

  return (
    <div className="card-container" style={{background:'var(--bg-dark)', border:'1px solid var(--border)', borderRadius:'12px', overflow:'hidden'}}>
      <div className="mono" style={{padding:'10px 14px', fontSize:'10px', background:'var(--secondary)', color:'#fff', display:'flex', justifyContent:'space-between'}}>
         <span>{title.toUpperCase()}</span>
         <span>{nodes.length} N</span>
      </div>
      
      <svg width="100%" height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
        {edges.map(e => {
          const from = positions[e.source_id], to = positions[e.target_id];
          if (!from || !to) return null;
          return <line key={e.id} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="var(--border)" strokeWidth={Math.max(1, e.strength * 3)} opacity={0.4} />;
        })}
        {nodes.map(n => {
          const p = positions[n.id];
          const active = hovered?.id === n.id;
          return (
            <g key={n.id} onMouseEnter={() => setHovered(n)} onMouseLeave={() => setHovered(null)}>
              <circle cx={p.x} cy={p.y} r={active ? 6 : 4} fill={active ? 'var(--accent)' : 'var(--secondary)'} style={{transition:'all 0.2s'}} />
              {active && (
                <text x={p.x + 8} y={p.y + 4} className="mono" style={{fontSize:'10px', fill:'var(--text)', fontWeight:'bold'}}>
                  {n.label.toUpperCase()}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      
      <div className="mono" style={{padding:'8px 12px', fontSize:'9px', background:'rgba(0,0,0,0.05)', minHeight:'32px', color:'var(--muted)'}}>
        {hovered ? `NODE: ${hovered.label} | ACCESS: ${hovered.access_count}` : 'HOVER NODE TO INSPECT'}
      </div>
    </div>
  );
}
