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
    </defs>
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
      {/* Active ripple */}
      {isActive && (
        <circle cx={x} cy={y} r={r} fill="none" stroke={color} strokeWidth={1} opacity={0}>
          <animate attributeName="r" values={`${r};${r + 15}`} dur="1.5s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.4;0" dur="1.5s" repeatCount="indefinite" />
        </circle>
      )}
      {/* Selected ring */}
      {selected && (
        <circle cx={x} cy={y} r={r + 4} fill="none" stroke={GOLD} strokeWidth={2} opacity={0.6}>
          <animate attributeName="opacity" values="0.6;0.3;0.6" dur="2s" repeatCount="indefinite" />
        </circle>
      )}
      {/* Node */}
      <circle cx={x} cy={y} r={r} fill={SURFACE} stroke={color}
        strokeWidth={isActive || selected ? 2 : isDone ? 1.5 : 0.8} />
      {/* Label or check */}
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

// ── Thinking Bubble ──────────────────────────────────────────────

function ThinkingBubble({ agent, x, y, onClose }: {
  agent: AgentState; x: number; y: number; onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [agent.thinking]);

  const bubbleW = 380;
  const bubbleH = 300;
  const bx = Math.min(Math.max(x - bubbleW / 2, 5), SVG_SIZE - bubbleW - 5);
  const by = y < CENTER ? y + 25 : y - bubbleH - 25;

  const color = statusColor(agent.status, agent.resultado);
  const statusLabel = agent.status === "active" ? "Analizando..." : agent.status === "done" ? "Completado" : agent.status === "error" ? "Error" : "En espera";

  return (
    <foreignObject x={bx} y={by} width={bubbleW} height={bubbleH}>
      <div
        style={{
          background: "white",
          border: `1px solid ${color}`,
          boxShadow: `0 4px 20px rgba(0,0,0,0.08), 0 0 0 1px rgba(154,123,45,0.1)`,
          fontSize: "10px",
          fontFamily: "'Inter', sans-serif",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          height: "100%",
        }}
      >
        {/* Header */}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "6px 8px", borderBottom: "1px solid #E2DED6",
        }}>
          <span style={{ fontWeight: 700, color: "#1A1A1A" }}>Agente {agent.id + 1}</span>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ color, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {statusLabel}
            </span>
            <button onClick={onClose} style={{
              background: "none", border: "none", cursor: "pointer",
              color: "#8C8579", fontSize: "14px", lineHeight: 1,
            }}>×</button>
          </div>
        </div>
        {/* Thinking text */}
        <div ref={ref} style={{
          flex: 1, overflowY: "auto", padding: "6px 8px",
          color: "#4A4640", lineHeight: 1.5, whiteSpace: "pre-wrap",
        }}>
          {agent.thinking || (agent.status === "idle" ? "Esperando turno..." : "Procesando...")}
        </div>
      </div>
    </foreignObject>
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

// ── Main Panel ───────────────────────────────────────────────────

export function AgentSwarmPanel({ swarmProgress }: { swarmProgress: SwarmProgress }) {
  const { step, progress, detail, agents, synthesizerActive, costUsd, totalAgents } = swarmProgress;
  const [selectedId, setSelectedId] = useState<number | null>(null);

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

  const selectedAgent = selectedId !== null ? agents.find(a => a.id === selectedId) : null;
  const selectedPos = selectedId !== null ? positions.find(p => p.id === selectedId) : null;

  const counts = useMemo(() => {
    const done = agents.filter(a => a.status === "done").length;
    const active = agents.filter(a => a.status === "active").length;
    const idle = agents.filter(a => a.status === "idle").length;
    const errors = agents.filter(a => a.status === "error").length;
    return { done, active, idle, errors };
  }, [agents]);

  return (
    <div className="bg-[var(--surface)] border border-[var(--outline-variant)] p-5 space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] font-semibold tracking-[0.15em] uppercase text-[var(--primary)]">
          {step === "done" ? "Análisis completo" : "Analizando jurisprudencia..."}
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-[11px] px-3 py-1 tracking-wide uppercase bg-[var(--container-lowest)] text-[var(--primary)]">
            {agents.length} agentes
          </span>
          {costUsd > 0 && (
            <span className="text-[11px] font-bold text-[var(--primary)] font-heading">
              ${costUsd.toFixed(4)}
            </span>
          )}
        </div>
      </div>

      {/* SVG Graph */}
      <div className="flex justify-center">
        <svg width="100%" viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`} style={{ maxWidth: 400, maxHeight: 400 }}>
          <SvgDefs />

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

          {/* Thinking bubble — agent */}
          {selectedAgent && selectedPos && (
            <ThinkingBubble
              agent={selectedAgent}
              x={selectedPos.x} y={selectedPos.y}
              onClose={() => setSelectedId(null)} />
          )}

          {/* Thinking bubble — synthesizer/orchestrator */}
          {selectedId === -1 && (
            <ThinkingBubble
              agent={{
                id: -1,
                status: supervisorStatus === "active" ? "active" : "done",
                thinking: swarmProgress.synthThinking || (supervisorStatus === "active" ? "Sintetizando análisis..." : "Click para ver resumen"),
              }}
              x={CENTER} y={CENTER}
              onClose={() => setSelectedId(null)} />
          )}
        </svg>
      </div>

      {/* Progress */}
      <ProgressBar progress={progress} detail={detail} />

      {/* Agent stats */}
      <div className="flex justify-center gap-6 text-[11px] text-[var(--muted)]">
        <span><span style={{ color: GOLD_DONE }}>✓</span> {counts.done} completados</span>
        <span><span style={{ color: GOLD_LIGHT }}>●</span> {counts.active} leyendo</span>
        <span><span style={{ color: GOLD_DIM }}>●</span> {counts.idle} en espera</span>
        {counts.errors > 0 && <span><span style={{ color: DANGER }}>●</span> {counts.errors} errores</span>}
      </div>

      <p className="text-center text-[10px] text-[var(--muted)] italic">
        Tocá un agente para ver qué está analizando
      </p>
    </div>
  );
}
