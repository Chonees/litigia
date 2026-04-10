"use client";

import { useEffect, useRef, useState, useMemo, useCallback } from "react";

// ── Types ────────────────────────────────────────────────────────

export interface AgentState {
  id: number;
  status: "idle" | "active" | "done" | "error";
  thinking?: string;
  resultado?: string;
}

export interface SwarmProgress {
  step: "search" | "analyze" | "synthesize" | "done";
  progress: number;
  detail: string;
  agents: AgentState[];
  synthesizerActive: boolean;
  costUsd: number;
  totalAgents: number;
  synthThinking?: string;
}

// ── Layout ───────────────────────────────────────────────────────

const SVG_SIZE = 360;
const CENTER = SVG_SIZE / 2;
const ORBIT_RADIUS = 130;
const NODE_R_CENTER = 24;
const MIN_ZOOM = 0.4;
const MAX_ZOOM = 3;
const DOT_GRID_SPACING = 16;

function getNodeRadius(total: number): number {
  if (total <= 15) return 16;
  if (total <= 30) return 13;
  if (total <= 50) return 10;
  return 8;
}

function agentPos(index: number, total: number) {
  const angle = (index * 2 * Math.PI) / total - Math.PI / 2;
  return { x: CENTER + ORBIT_RADIUS * Math.cos(angle), y: CENTER + ORBIT_RADIUS * Math.sin(angle) };
}

// ── Responsive hook ─────────────────────────────────────────────

function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [breakpoint]);
  return isMobile;
}

// ── Colors ───────────────────────────────────────────────────────

const GOLD = "#9A7B2D";
const GOLD_LIGHT = "#B08A30";
const GOLD_DIM = "rgba(154, 123, 45, 0.15)";
const GOLD_DONE = "#B08A30";
const SURFACE = "#FFFFFF";
const DANGER = "#C62828";

const RESULTADO_COLORS: Record<string, string> = {
  favorable: "#2E7D32",
  desfavorable: "#C62828",
  parcial: "#9A7B2D",
  inadmisible: "#8C8579",
};

function statusColor(s: AgentState["status"], resultado?: string) {
  if (s === "done" && resultado) return RESULTADO_COLORS[resultado] || GOLD_DONE;
  if (s === "active") return GOLD_LIGHT;
  if (s === "done") return GOLD_DONE;
  if (s === "error") return DANGER;
  return GOLD_DIM;
}

// ── SVG Defs ─────────────────────────────────────────────────────

function SvgDefs() {
  return (
    <defs>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
      <pattern id="dot-grid" x="0" y="0" width={DOT_GRID_SPACING} height={DOT_GRID_SPACING} patternUnits="userSpaceOnUse">
        <circle cx={DOT_GRID_SPACING / 2} cy={DOT_GRID_SPACING / 2} r="1" fill={GOLD} opacity="0.35" />
      </pattern>
    </defs>
  );
}

// ── Control Icons (inline SVG) ──────────────────────────────────

function IconZoomIn() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /><line x1="11" y1="8" x2="11" y2="14" /><line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  );
}

function IconZoomOut() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /><line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  );
}

function IconReset() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
    </svg>
  );
}

function IconFullscreen() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 3 21 3 21 9" /><polyline points="9 21 3 21 3 15" /><line x1="21" y1="3" x2="14" y2="10" /><line x1="3" y1="21" x2="10" y2="14" />
    </svg>
  );
}

function IconExitFullscreen() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 14 10 14 10 20" /><polyline points="20 10 14 10 14 4" /><line x1="14" y1="10" x2="21" y2="3" /><line x1="3" y1="21" x2="10" y2="14" />
    </svg>
  );
}

function IconClose() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

// ── Connection Line ──────────────────────────────────────────────

function Edge({ x1, y1, x2, y2, active, done, r1, r2 }: {
  x1: number; y1: number; x2: number; y2: number;
  active: boolean; done: boolean; r1: number; r2: number;
}) {
  const dx = x2 - x1, dy = y2 - y1, dist = Math.sqrt(dx * dx + dy * dy);
  const ux = dx / dist, uy = dy / dist;
  const sx = x1 + ux * (r1 + 3), sy = y1 + uy * (r1 + 3);
  const ex = x2 - ux * (r2 + 3), ey = y2 - uy * (r2 + 3);

  return (
    <g>
      <line x1={sx} y1={sy} x2={ex} y2={ey}
        stroke={done ? GOLD_DONE : active ? GOLD : GOLD_DIM}
        strokeWidth={active ? 1.2 : 0.5}
        strokeDasharray={active ? "none" : "2 3"}
        opacity={done ? 0.4 : active ? 0.7 : 0.15} />
      {active && (
        <circle r={2} fill={GOLD_LIGHT} filter="url(#glow)">
          <animateMotion dur="1s" repeatCount="indefinite" path={`M${sx},${sy} L${ex},${ey}`} />
        </circle>
      )}
    </g>
  );
}

// ── Agent Node ───────────────────────────────────────────────────

function AgentNode({ x, y, r, label, status, resultado, isCenter, selected, onClick }: {
  x: number; y: number; r: number; label: string;
  status: AgentState["status"]; resultado?: string;
  isCenter?: boolean; selected?: boolean; onClick?: () => void;
}) {
  const isActive = status === "active";
  const isDone = status === "done";
  const color = isCenter
    ? (isActive ? GOLD_LIGHT : isDone ? GOLD_DONE : GOLD)
    : statusColor(status, resultado);

  return (
    <g style={{ cursor: "pointer" }} onClick={onClick}>
      {isActive && (
        <circle cx={x} cy={y} r={r} fill="none" stroke={color} strokeWidth={1} opacity={0}>
          <animate attributeName="r" values={`${r};${r + 15}`} dur="1.5s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.4;0" dur="1.5s" repeatCount="indefinite" />
        </circle>
      )}
      {selected && (
        <circle cx={x} cy={y} r={r + 4} fill="none" stroke={GOLD} strokeWidth={2} opacity={0.6}>
          <animate attributeName="opacity" values="0.6;0.3;0.6" dur="2s" repeatCount="indefinite" />
        </circle>
      )}
      <circle cx={x} cy={y} r={r} fill={SURFACE} stroke={color}
        strokeWidth={isActive || selected ? 2 : isDone ? 1.5 : 0.8} />
      {isDone && !isCenter ? (
        <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="central"
          fontSize={r * 0.7} fill={color}>✓</text>
      ) : (
        <text x={x} y={y + 1} textAnchor="middle" dominantBaseline="central"
          fontSize={isCenter ? 9 : Math.max(6, r * 0.55)} fontFamily="'Inter', sans-serif"
          fontWeight={600} fill={color}>{label}</text>
      )}
    </g>
  );
}

// ── Thinking Panel (click on agent → final result) ──────────────

function ThinkingPanel({ agent, onClose, isMobile }: {
  agent: AgentState;
  onClose: () => void;
  isMobile: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [agent.thinking]);

  const color = statusColor(agent.status, agent.resultado);
  const statusLabel = agent.status === "active" ? "Analizando..."
    : agent.status === "done" ? "Completado"
    : agent.status === "error" ? "Error"
    : "En espera";

  const panelStyle: React.CSSProperties = isMobile
    ? {
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        height: "60%",
        borderTop: `2px solid ${color}`,
        borderRadius: "12px 12px 0 0",
        boxShadow: "0 -4px 20px rgba(0,0,0,0.1)",
      }
    : {
        position: "absolute",
        top: 0,
        right: 0,
        bottom: 0,
        width: "min(360px, 45%)",
        borderLeft: `2px solid ${color}`,
        boxShadow: "-4px 0 20px rgba(0,0,0,0.08)",
      };

  return (
    <div
      style={{
        ...panelStyle,
        background: SURFACE,
        display: "flex",
        flexDirection: "column",
        zIndex: 20,
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: isMobile ? "12px 16px" : "10px 14px",
        borderBottom: "1px solid #E2DED6", flexShrink: 0,
      }}>
        <span style={{ fontWeight: 700, fontSize: isMobile ? 14 : 12, color: "#1A1A1A" }}>
          {agent.id === -1 ? "Sintetizador" : `Agente ${agent.id + 1}`}
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ color, fontWeight: 600, fontSize: isMobile ? 11 : 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {statusLabel}
          </span>
          <button onClick={onClose} style={{
            background: "none", border: "none", cursor: "pointer",
            color: "#8C8579",
            padding: isMobile ? "6px" : "2px 4px",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <IconClose />
          </button>
        </div>
      </div>
      {/* Thinking text — full scroll */}
      <div ref={ref} style={{
        flex: 1, overflowY: "auto", padding: isMobile ? "14px 16px" : "12px 14px",
        color: "#4A4640", lineHeight: 1.6, whiteSpace: "pre-wrap",
        fontSize: isMobile ? 13 : 12,
        WebkitOverflowScrolling: "touch",
      }}>
        {agent.thinking || (agent.status === "idle" ? "Esperando turno..." : "Procesando...")}
      </div>
    </div>
  );
}

// ── Progress Bar ─────────────────────────────────────────────────

function ProgressBar({ progress, detail }: { progress: number; detail: string }) {
  return (
    <div className="space-y-2">
      <div className="h-1 overflow-hidden" style={{ background: "var(--outline-variant)" }}>
        <div className="h-full gold-gradient transition-all duration-500 ease-out" style={{ width: `${progress}%` }} />
      </div>
      <div className="flex justify-between items-center">
        <span className="text-[11px] text-[var(--muted)]">{detail}</span>
        <span className="text-[11px] font-semibold text-[var(--primary)]">{progress}%</span>
      </div>
    </div>
  );
}

// ── Graph Controls ──────────────────────────────────────────────

function GraphControlBtn({ onClick, title, children }: {
  onClick: () => void; title: string; children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        background: "rgba(255,255,255,0.85)",
        borderColor: "rgba(154,123,45,0.2)",
        color: "#8C8579",
        padding: 6,
        borderRadius: 8,
        border: "1px solid rgba(154,123,45,0.2)",
        backdropFilter: "blur(4px)",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minWidth: 32,
        minHeight: 32,
      }}
    >
      {children}
    </button>
  );
}

// ── Main Panel ───────────────────────────────────────────────────

export function AgentSwarmPanel({ swarmProgress }: { swarmProgress: SwarmProgress }) {
  const { step, progress, detail, agents, synthesizerActive, costUsd, totalAgents } = swarmProgress;
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [zoom, setZoom] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isFullscreen, setIsFullscreen] = useState(false);

  const isMobile = useIsMobile();
  const svgRef = useRef<SVGSVGElement>(null);
  const panRef = useRef<{ startX: number; startY: number; origPanX: number; origPanY: number } | null>(null);
  const pinchRef = useRef<{ dist: number; zoom: number } | null>(null);
  const zoomRef = useRef(zoom);
  zoomRef.current = zoom;

  const nodeR = getNodeRadius(totalAgents);

  const positions = useMemo(
    () => agents.map((a, i) => ({ ...agentPos(i, agents.length), id: a.id })),
    [agents.length],
  );

  const supervisorStatus = step === "done" ? "done" as const
    : synthesizerActive ? "active" as const
    : step === "search" ? "active" as const
    : agents.some(a => a.status === "active") ? "active" as const
    : "idle" as const;

  const centerLabel = synthesizerActive ? "SYN" : "ORQ";

  const handleClick = useCallback((id: number) => {
    setSelectedId(prev => prev === id ? null : id);
  }, []);

  const selectedAgent = selectedId !== null
    ? selectedId === -1
      ? {
          id: -1,
          status: (supervisorStatus === "active" ? "active" : "done") as AgentState["status"],
          thinking: swarmProgress.synthThinking || (supervisorStatus === "active" ? "Sintetizando análisis..." : "Click para ver resumen"),
        }
      : agents.find(a => a.id === selectedId) ?? null
    : null;

  const counts = useMemo(() => {
    const done = agents.filter(a => a.status === "done").length;
    const active = agents.filter(a => a.status === "active").length;
    const idle = agents.filter(a => a.status === "idle").length;
    const errors = agents.filter(a => a.status === "error").length;
    return { done, active, idle, errors };
  }, [agents]);

  // ── Zoom controls ──
  const handleZoomIn = useCallback(() => {
    setZoom(z => Math.min(MAX_ZOOM, z * 1.3));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom(z => Math.max(MIN_ZOOM, z / 1.3));
  }, []);

  const handleReset = useCallback(() => {
    setZoom(1);
    setPanOffset({ x: 0, y: 0 });
  }, []);

  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen(prev => !prev);
  }, []);

  // ── Mouse wheel zoom (desktop) ──
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const handler = (e: WheelEvent) => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
      const nz = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoomRef.current * factor));

      const rect = svg.getBoundingClientRect();
      const vs = SVG_SIZE / zoomRef.current;
      const mx = panOffset.x + ((e.clientX - rect.left) / rect.width) * vs;
      const my = panOffset.y + ((e.clientY - rect.top) / rect.height) * vs;

      const newVs = SVG_SIZE / nz;
      setPanOffset({
        x: mx - ((e.clientX - rect.left) / rect.width) * newVs,
        y: my - ((e.clientY - rect.top) / rect.height) * newVs,
      });
      setZoom(nz);
    };

    svg.addEventListener("wheel", handler, { passive: false });
    return () => svg.removeEventListener("wheel", handler);
  }, [panOffset]);

  // ── Pointer handlers (pan + pinch-to-zoom) ──
  const pointersRef = useRef<Map<number, PointerEvent>>(new Map());

  function getTouchDist(pointers: Map<number, PointerEvent>): number {
    const pts = Array.from(pointers.values());
    if (pts.length < 2) return 0;
    const dx = pts[1].clientX - pts[0].clientX;
    const dy = pts[1].clientY - pts[0].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    const target = e.target as SVGElement;
    const isBg = target.tagName === "svg" || target.tagName === "rect";

    pointersRef.current.set(e.pointerId, e.nativeEvent);

    if (pointersRef.current.size === 2) {
      // Start pinch — capture for both pointers
      (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
      pinchRef.current = { dist: getTouchDist(pointersRef.current), zoom: zoomRef.current };
      panRef.current = null;
    } else if (pointersRef.current.size === 1 && isBg) {
      // Pan — only capture when clicking background, not nodes
      (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
      panRef.current = { startX: e.clientX, startY: e.clientY, origPanX: panOffset.x, origPanY: panOffset.y };
    }
  }, [panOffset]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    pointersRef.current.set(e.pointerId, e.nativeEvent);

    // Pinch-to-zoom
    if (pointersRef.current.size === 2 && pinchRef.current) {
      const newDist = getTouchDist(pointersRef.current);
      if (newDist > 0 && pinchRef.current.dist > 0) {
        const scale = newDist / pinchRef.current.dist;
        setZoom(Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, pinchRef.current.zoom * scale)));
      }
      return;
    }

    // Pan
    const pan = panRef.current;
    if (!pan) return;
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const vs = SVG_SIZE / zoom;
    const dx = ((e.clientX - pan.startX) / rect.width) * vs;
    const dy = ((e.clientY - pan.startY) / rect.height) * vs;
    setPanOffset({ x: pan.origPanX - dx, y: pan.origPanY - dy });
  }, [zoom]);

  const handlePointerUp = useCallback((e: React.PointerEvent) => {
    pointersRef.current.delete(e.pointerId);
    if (pointersRef.current.size < 2) pinchRef.current = null;
    if (pointersRef.current.size === 0) panRef.current = null;
  }, []);

  // ── Escape to exit fullscreen ──
  useEffect(() => {
    if (!isFullscreen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isFullscreen]);

  // ── Computed viewBox ──
  const viewSize = SVG_SIZE / zoom;
  const viewBox = `${panOffset.x} ${panOffset.y} ${viewSize} ${viewSize}`;

  // ── SVG height: responsive ──
  const svgHeight = isFullscreen ? "100%" : isMobile ? 280 : 400;

  const graphContent = (
    <div className="relative" style={{ touchAction: "none", height: isFullscreen ? "100%" : isMobile ? 280 : 400 }}>
      {/* Zoom & fullscreen controls */}
      <div className="absolute top-2 right-2 z-10 flex flex-col gap-1">
        {!isMobile && (
          <>
            <GraphControlBtn onClick={handleZoomIn} title="Zoom in"><IconZoomIn /></GraphControlBtn>
            <GraphControlBtn onClick={handleZoomOut} title="Zoom out"><IconZoomOut /></GraphControlBtn>
            <GraphControlBtn onClick={handleReset} title="Resetear vista"><IconReset /></GraphControlBtn>
            <div style={{ height: 4 }} />
          </>
        )}
        <GraphControlBtn onClick={handleToggleFullscreen} title={isFullscreen ? "Salir" : "Pantalla completa"}>
          {isFullscreen ? <IconExitFullscreen /> : <IconFullscreen />}
        </GraphControlBtn>
      </div>

      {/* Mobile: zoom buttons row at bottom-left */}
      {isMobile && (
        <div className="absolute bottom-2 left-2 z-10 flex gap-1">
          <GraphControlBtn onClick={handleZoomOut} title="Zoom out"><IconZoomOut /></GraphControlBtn>
          <GraphControlBtn onClick={handleReset} title="Reset"><IconReset /></GraphControlBtn>
          <GraphControlBtn onClick={handleZoomIn} title="Zoom in"><IconZoomIn /></GraphControlBtn>
        </div>
      )}

      <svg
        ref={svgRef}
        width="100%"
        height={svgHeight}
        viewBox={viewBox}
        preserveAspectRatio="xMidYMid meet"
        style={{
          cursor: panRef.current ? "grabbing" : "grab",
          background: SURFACE,
          borderRadius: isFullscreen ? 0 : 4,
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        <SvgDefs />

        {/* Dot grid background */}
        <rect x={panOffset.x - 500} y={panOffset.y - 500} width={viewSize + 1000} height={viewSize + 1000}
          fill="url(#dot-grid)" style={{ pointerEvents: "none" }} />

        {/* Orbit */}
        <circle cx={CENTER} cy={CENTER} r={ORBIT_RADIUS} fill="none" stroke={GOLD_DIM} strokeWidth={0.5} strokeDasharray="3 4" />

        {/* Edges */}
        {positions.map(({ x, y, id }) => {
          const agent = agents.find(a => a.id === id);
          return (
            <Edge key={`e-${id}`} x1={CENTER} y1={CENTER} x2={x} y2={y}
              active={agent?.status === "active"} done={agent?.status === "done"}
              r1={NODE_R_CENTER} r2={nodeR} />
          );
        })}

        {/* Agent nodes */}
        {positions.map(({ x, y, id }) => {
          const agent = agents.find(a => a.id === id);
          return (
            <AgentNode key={`a-${id}`} x={x} y={y} r={nodeR}
              label={`${id + 1}`} status={agent?.status ?? "idle"}
              resultado={agent?.resultado}
              selected={selectedId === id}
              onClick={() => handleClick(id)} />
          );
        })}

        {/* Center node */}
        <AgentNode x={CENTER} y={CENTER} r={NODE_R_CENTER}
          label={centerLabel} status={supervisorStatus} isCenter
          selected={selectedId === -1}
          onClick={() => setSelectedId(prev => prev === -1 ? null : -1)} />
      </svg>

      {/* Thinking panel — HTML overlay, outside SVG */}
      {selectedAgent && (
        <ThinkingPanel agent={selectedAgent} onClose={() => setSelectedId(null)} isMobile={isMobile} />
      )}
    </div>
  );

  // ── Fullscreen overlay ──
  if (isFullscreen) {
    return (
      <div
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 50,
          background: SURFACE,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Fullscreen header */}
        <div
          className="flex items-center justify-between gap-3"
          style={{
            borderBottom: "1px solid #E2DED6",
            flexShrink: 0,
            padding: isMobile ? "10px 16px" : "12px 24px",
            flexWrap: "wrap",
          }}
        >
          <h3 style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.15em",
            textTransform: "uppercase" as const,
            color: GOLD,
          }}>
            {step === "done" ? "Análisis completo" : "Analizando jurisprudencia..."}
          </h3>
          <div className="flex items-center gap-3" style={{ flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase" as const, color: "#8C8579" }}>
              {agents.length} agentes
            </span>
            {costUsd > 0 && (
              <span style={{ fontSize: 11, fontWeight: 700, color: GOLD }}>
                ${costUsd.toFixed(4)}
              </span>
            )}
            <div className="flex gap-3" style={{ fontSize: 11, color: "#8C8579" }}>
              <span><span style={{ color: GOLD_DONE }}>✓</span> {counts.done}</span>
              <span><span style={{ color: GOLD_LIGHT }}>●</span> {counts.active}</span>
              <span><span style={{ color: GOLD_DIM }}>●</span> {counts.idle}</span>
              {counts.errors > 0 && <span><span style={{ color: DANGER }}>●</span> {counts.errors}</span>}
            </div>
          </div>
        </div>
        {/* Graph fills remaining space */}
        <div style={{ flex: 1, minHeight: 0 }}>
          {graphContent}
        </div>
        {/* Footer progress */}
        <div style={{
          borderTop: "1px solid #E2DED6",
          flexShrink: 0,
          padding: isMobile ? "10px 16px" : "12px 24px",
        }}>
          <ProgressBar progress={progress} detail={detail} />
        </div>
      </div>
    );
  }

  // ── Normal layout ──
  return (
    <div className="bg-[var(--surface)] border border-[var(--outline-variant)] p-4 md:p-5 space-y-3 md:space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h3 className="text-[11px] font-semibold tracking-[0.15em] uppercase text-[var(--primary)]">
          {step === "done" ? "Análisis completo" : "Analizando jurisprudencia..."}
        </h3>
        <div className="flex items-center gap-2 md:gap-3">
          <span className="text-[10px] md:text-[11px] px-2 md:px-3 py-1 tracking-wide uppercase bg-[var(--container-lowest)] text-[var(--primary)]">
            {agents.length} agentes
          </span>
          {costUsd > 0 && (
            <span className="text-[10px] md:text-[11px] font-bold text-[var(--primary)] font-heading">
              ${costUsd.toFixed(4)}
            </span>
          )}
        </div>
      </div>

      {/* SVG Graph + Thinking panel */}
      {graphContent}

      {/* Progress */}
      <ProgressBar progress={progress} detail={detail} />

      {/* Agent stats */}
      <div className="flex justify-center flex-wrap gap-3 md:gap-6 text-[10px] md:text-[11px] text-[var(--muted)]">
        <span><span style={{ color: GOLD_DONE }}>✓</span> {counts.done} completados</span>
        <span><span style={{ color: GOLD_LIGHT }}>●</span> {counts.active} leyendo</span>
        <span><span style={{ color: GOLD_DIM }}>●</span> {counts.idle} en espera</span>
        {counts.errors > 0 && <span><span style={{ color: DANGER }}>●</span> {counts.errors} errores</span>}
      </div>

      <p className="text-center text-[9px] md:text-[10px] text-[var(--muted)] italic">
        Tocá un agente para ver qué está analizando
      </p>
    </div>
  );
}
