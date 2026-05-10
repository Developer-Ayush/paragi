"use client";

import React from "react";

export default function Logo({ theme = "light", className = "" }) {
  const isDark = theme === "dark";

  // Colors
  const hubColor = isDark ? "#ff6b3d" : "#9f3b19";
  const edgeColor = isDark ? "#d4b483" : "#c9b08a";
  const nodeFill = isDark ? "#2a241d" : "#ede4d2";
  const nodeStroke = isDark ? "#8c7b64" : "#6c5b44";
  const textColor = isDark ? "#f4f1ea" : "#1f1a14";
  const dividerColor = isDark ? "#4a443d" : "#d7c2a0";
  const crossEdgeColor = isDark ? "#3d362a" : "#e8d8bc";

  return (
    <svg
      width="100%"
      style={{ height: 'auto' }}
      viewBox="0 0 680 165"
      role="img"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
        <title>Paragi</title>
        <desc>Paragi logo — hexagonal knowledge graph mark with hub node and weighted edges, beside the Paragi wordmark</desc>

        {/* Skip cross-edges (very faint, dashed — deeper graph connectivity) */}
        <line x1="100" y1="30" x2="145" y2="56" stroke={crossEdgeColor} strokeWidth="1.0" strokeLinecap="round" />
        <line x1="145" y1="56" x2="100" y2="134" stroke={crossEdgeColor} strokeWidth="0.8" strokeLinecap="round" strokeDasharray="4 3" />
        <line x1="55" y1="56" x2="145" y2="108" stroke={crossEdgeColor} strokeWidth="0.8" strokeLinecap="round" strokeDasharray="4 3" />

        {/* Outer ring edges */}
        <line x1="100" y1="30" x2="145" y2="56" stroke={edgeColor} strokeWidth="1.5" strokeLinecap="round" />
        <line x1="145" y1="56" x2="145" y2="108" stroke={edgeColor} strokeWidth="1.8" strokeLinecap="round" />
        <line x1="145" y1="108" x2="100" y2="134" stroke={edgeColor} strokeWidth="1.4" strokeLinecap="round" />
        <line x1="100" y1="134" x2="55" y2="108" stroke={edgeColor} strokeWidth="1.6" strokeLinecap="round" />
        <line x1="55" y1="108" x2="55" y2="56" stroke={edgeColor} strokeWidth="1.2" strokeLinecap="round" />
        <line x1="55" y1="56" x2="100" y2="30" stroke={edgeColor} strokeWidth="1.5" strokeLinecap="round" />

        {/* Hub spokes — accent color, varying weight encodes edge strength */}
        <line x1="100" y1="82" x2="100" y2="30" stroke={hubColor} strokeWidth="4.6" strokeLinecap="round" />
        <line x1="100" y1="82" x2="145" y2="56" stroke={hubColor} strokeWidth="4.1" strokeLinecap="round" />
        <line x1="100" y1="82" x2="145" y2="108" stroke={hubColor} strokeWidth="3.5" strokeLinecap="round" />
        <line x1="100" y1="82" x2="100" y2="134" stroke={hubColor} strokeWidth="3.8" strokeLinecap="round" />
        <line x1="100" y1="82" x2="55" y2="108" stroke={hubColor} strokeWidth="2.9" strokeLinecap="round" />
        <line x1="100" y1="82" x2="55" y2="56" stroke={hubColor} strokeWidth="3.2" strokeLinecap="round" />

        {/* Outer nodes — pure points, no meaning of their own */}
        <circle cx="100" cy="30" r="5" fill={nodeFill} stroke={nodeStroke} strokeWidth="1.5" />
        <circle cx="145" cy="56" r="5" fill={nodeFill} stroke={nodeStroke} strokeWidth="1.5" />
        <circle cx="145" cy="108" r="5" fill={nodeFill} stroke={nodeStroke} strokeWidth="1.5" />
        <circle cx="100" cy="134" r="5" fill={nodeFill} stroke={nodeStroke} strokeWidth="1.5" />
        <circle cx="55" cy="108" r="5" fill={nodeFill} stroke={nodeStroke} strokeWidth="1.5" />
        <circle cx="55" cy="56" r="5" fill={nodeFill} stroke={nodeStroke} strokeWidth="1.5" />

        {/* Hub node — larger, filled center dot */}
        <circle cx="100" cy="82" r="8.5" fill={isDark ? "#1a1612" : "#fff4e2"} stroke={hubColor} strokeWidth="2.5" />
        <circle cx="100" cy="82" r="3.5" fill={hubColor} />

        {/* Wordmark */}
        <text
          x="200"
          y="107"
          fontFamily="'Libre Baskerville', serif"
          fontSize="72"
          fontWeight="700"
          letterSpacing="-1.5"
          fill={textColor}
        >
          Paragi
        </text>

        {/* Divider */}
        <line x1="188" y1="48" x2="188" y2="122" stroke={dividerColor} strokeWidth="0.8" />
      </svg>
  );
}
