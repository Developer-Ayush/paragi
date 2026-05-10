"use client";

import { useMemo, useState } from "react";

const WIDTH = 540;
const HEIGHT = 270;
const PAD = 22;

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

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function buildPositions(nodes, edges) {
  const positions = {};
  const neighborMap = {};

  nodes.forEach((node) => {
    neighborMap[node.id] = new Set();
  });

  edges.forEach((edge) => {
    if (!neighborMap[edge.source_id] || !neighborMap[edge.target_id]) return;
    neighborMap[edge.source_id].add(edge.target_id);
    neighborMap[edge.target_id].add(edge.source_id);
  });

  nodes.forEach((node, index) => {
    const seedX = hashText(`${node.id}:${index}`);
    const seedY = hashText(`${index}:${node.id}`);
    positions[node.id] = {
      x: PAD + (seedX % (WIDTH - PAD * 2)),
      y: PAD + (seedY % (HEIGHT - PAD * 2)),
    };
  });

  for (let step = 0; step < 90; step += 1) {
    nodes.forEach((nodeA, idxA) => {
      const a = positions[nodeA.id];
      if (!a) return;

      let fx = 0;
      let fy = 0;

      nodes.forEach((nodeB, idxB) => {
        if (idxA === idxB) return;
        const b = positions[nodeB.id];
        if (!b) return;
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.hypot(dx, dy) || 0.001;
        if (dist < 30) {
          const repel = (30 - dist) * 0.08;
          fx += (dx / dist) * repel;
          fy += (dy / dist) * repel;
        }
      });

      const neighbors = neighborMap[nodeA.id] || new Set();
      neighbors.forEach((neighborId) => {
        const b = positions[neighborId];
        if (!b) return;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.hypot(dx, dy) || 0.001;
        const desired = 76;
        const pull = (dist - desired) * 0.0048;
        fx += (dx / dist) * pull;
        fy += (dy / dist) * pull;
      });

      a.x = clamp(a.x + fx, PAD, WIDTH - PAD);
      a.y = clamp(a.y + fy, PAD, HEIGHT - PAD);
    });
  }

  return positions;
}

export default function GraphCanvas({ title, summary, nodeLimit = 26, edgeLimit = 60, showLabels = "hover" }) {
  const [hoveredNode, setHoveredNode] = useState(null);
  const [hoveredEdge, setHoveredEdge] = useState(null);

  const { nodes, edges, positions } = useMemo(() => {
    const selectedNodes = (summary?.nodes || []).slice(0, Math.max(8, nodeLimit));
    const nodeSet = new Set(selectedNodes.map((node) => node.id));
    const selectedEdges = (summary?.edges || []).filter(
      (edge) => nodeSet.has(edge.source_id) && nodeSet.has(edge.target_id),
    ).slice(0, Math.max(12, edgeLimit));

    const pos = buildPositions(selectedNodes, selectedEdges);
    return { nodes: selectedNodes, edges: selectedEdges, positions: pos };
  }, [summary, nodeLimit, edgeLimit]);

  const hoverText = hoveredNode?.description || hoveredEdge?.description || "Hover a node or edge for full details.";

  return (
    <section className="graph-card">
      <header className="graph-card-head">
        <strong>{title}</strong>
        <span>
          {(summary?.stats?.total_nodes || 0)} nodes · {(summary?.stats?.total_edges || 0)} edges
        </span>
      </header>

      <svg className="graph-svg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`${title} graph`}>
        <rect x="0" y="0" width={WIDTH} height={HEIGHT} fill="transparent" rx="14" />

        {edges.map((edge) => {
          const from = positions[edge.source_id];
          const to = positions[edge.target_id];
          if (!from || !to) return null;
          const isActive = hoveredEdge?.id === edge.id;
          return (
            <line
              key={edge.id}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={isActive ? "var(--accent)" : "var(--graph-line)"}
              strokeOpacity={isActive ? 1.0 : 0.75}
              strokeWidth={Math.max(1.2, edge.strength * 4.2)}
              onMouseEnter={() => {
                setHoveredEdge(edge);
                setHoveredNode(null);
              }}
              onMouseLeave={() => setHoveredEdge(null)}
            />
          );
        })}

        {nodes.map((node) => {
          const p = positions[node.id];
          if (!p) return null;
          const active = hoveredNode?.id === node.id;
          const renderLabel = showLabels === "always" || active;
          return (
            <g
              key={node.id}
              onMouseEnter={() => {
                setHoveredNode(node);
                setHoveredEdge(null);
              }}
              onMouseLeave={() => setHoveredNode(null)}
            >
              <circle
                cx={p.x}
                cy={p.y}
                r={active ? 6.8 : 5.2}
                fill={active ? "var(--accent)" : "var(--graph-node)"}
              />
              {renderLabel && (
                <text
                  x={p.x + 7}
                  y={p.y - 8}
                  className="graph-label"
                >
                  {shorten(node.label, 14)}
                </text>
              )}
            </g>
          );
        })}

        {nodes.length === 0 && (
          <text x="16" y="28" className="graph-empty">No nodes yet.</text>
        )}
      </svg>

      <p className="graph-hover-text">{hoverText}</p>
    </section>
  );
}
