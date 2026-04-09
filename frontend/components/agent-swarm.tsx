"use client";

/**
 * AgentSwarmPanel — Real-time visualization of the analysis pipeline.
 *
 * Shows a central orchestrator node surrounded by reader agent nodes
 * in a circular orbit. Each node pulses when active, shows a gold check when done.
 * Click any node to see its role and current thinking in a glassmorphism modal.
 *
 * Design: LITIGIA gold/navy theme, glassmorphism, Georgia serif.
 * Background: animated floating dot grid.
 */

import { useEffect, useRef, useState, useMemo, useCallback } from "react";

// ── Types ────────────────────────────────────────────────────────

export interface AgentState {
  id: number;
  status: "idle" | "active" | "done" | "error";
  /** What this agent found — populated when done */
  thinking?: string;
}

export interface SwarmProgress {
  step: "search" | "analyze" | "synthesize" | "done";
  progress: number;
  detail: string;
  agents: AgentState[];
  synthesizerActive: boolean;
}

// ── Constants ────────────────────────────────────────────────────

const SVG_SIZE = 300;
const CENTER = SVG_SIZE / 2;
const ORBIT_RADIUS = 105;
const NODE_R_AGENT = 16;
const NODE_R_CENTER = 22;
const TOTAL_AGENTS = 10;

// LITIGIA palette — NO green, gold only
const GOLD = "#b08a30";
const GOLD_LIGHT = "#c9a84c";
const GOLD_DIM = "rgba(176, 138, 48, 0.3)";
const GOLD_DONE = "#c9a84c";
const NAVY = "#1a1a2e";
const TEXT_MUTED = "rgba(107, 104, 120, 0.8)";
const DANGER = "#dc2626";

// Agent role descriptions
const AGENT_ROLES: Record<string, { title: string; description: string }> = {
  ORQ: {
    title: "Orquestador",
    description:
      "Coordina el pipeline completo. Distribuye los fallos entre los lectores, monitorea el progreso y lanza al sintetizador cuando todos terminan.",
  },
  OPUS: {
    title: "Sintetizador (Opus)",
    description:
      "Recibe los 100 analisis estructurados y cruza patrones: estrategias exitosas vs fracasadas, normas mas citadas, precedentes clave, riesgos concretos. Genera el informe estrategico final.",
  },
};

for (let i = 0; i < TOTAL_AGENTS; i++) {
  AGENT_ROLES[`L${i + 1}`] = {
    title: `Lector ${i + 1}`,
    description: `Lee el texto completo de ~10 fallos asignados. Extrae resultado, normas citadas, precedentes, via procesal, doctrina aplicada, hechos determinantes, prueba decisiva, quantum y relevancia para el cliente.`,
  };
}

// ── Helpers ──────────────────────────────────────────────────────

function agentPos(index: number, total: number) {
  const angle = (index * 2 * Math.PI) / total - Math.PI / 2;
  return {
    x: CENTER + ORBIT_RADIUS * Math.cos(angle),
    y: CENTER + ORBIT_RADIUS * Math.sin(angle),
  };
}

function statusColor(status: AgentState["status"]) {
  if (status === "active") return GOLD_LIGHT;
  if (status === "done") return GOLD_DONE;
  if (status === "error") return DANGER;
  return GOLD_DIM;
}

// ── Animated Dot Background (Canvas) ────────────────────────────

interface Dot {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

function AnimatedDots() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dotsRef = useRef<Dot[]>([]);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = SVG_SIZE;
    const H = SVG_SIZE;
    canvas.width = W;
    canvas.height = H;

    // Initialize dots
    if (dotsRef.current.length === 0) {
      const dots: Dot[] = [];
      for (let i = 0; i < 60; i++) {
        dots.push({
          x: Math.random() * W,
          y: Math.random() * H,
          vx: (Math.random() - 0.5) * 0.3,
          vy: (Math.random() - 0.5) * 0.3,
        });
      }
      dotsRef.current = dots;
    }

    function animate() {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, W, H);

      for (const dot of dotsRef.current) {
        dot.x += dot.vx;
        dot.y += dot.vy;

        // Wrap around
        if (dot.x < 0) dot.x = W;
        if (dot.x > W) dot.x = 0;
        if (dot.y < 0) dot.y = H;
        if (dot.y > H) dot.y = 0;

        ctx.beginPath();
        ctx.arc(dot.x, dot.y, 1, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(176, 138, 48, 0.18)";
        ctx.fill();
      }

      // Draw faint connecting lines between nearby dots
      for (let i = 0; i < dotsRef.current.length; i++) {
        for (let j = i + 1; j < dotsRef.current.length; j++) {
          const a = dotsRef.current[i];
          const b = dotsRef.current[j];
          const dist = Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
          if (dist < 50) {
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(176, 138, 48, ${0.08 * (1 - dist / 50)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      animRef.current = requestAnimationFrame(animate);
    }

    animate();
    return () => cancelAnimationFrame(animRef.current);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none"
      style={{ width: "100%", height: "100%" }}
    />
  );
}

// ── SVG Defs ─────────────────────────────────────────────────────

function SvgDefs() {
  return (
    <defs>
      <filter id="glow-gold" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="4" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <radialGradient id="center-grad" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor={GOLD} stopOpacity="0.2" />
        <stop offset="100%" stopColor={GOLD} stopOpacity="0" />
      </radialGradient>
    </defs>
  );
}

// ── Connection Line with Particle ────────────────────────────────

function ConnectionLine({
  x1, y1, x2, y2, active, done,
}: {
  x1: number; y1: number; x2: number; y2: number;
  active: boolean; done: boolean;
}) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const ux = dx / dist;
  const uy = dy / dist;

  const sx = x1 + ux * (NODE_R_CENTER + 4);
  const sy = y1 + uy * (NODE_R_CENTER + 4);
  const ex = x2 - ux * (NODE_R_AGENT + 4);
  const ey = y2 - uy * (NODE_R_AGENT + 4);

  const lineColor = done ? GOLD_DONE : active ? GOLD : GOLD_DIM;
  const lineOpacity = done ? 0.5 : active ? 0.8 : 0.2;

  return (
    <g>
      <line
        x1={sx} y1={sy} x2={ex} y2={ey}
        stroke={lineColor}
        strokeWidth={active ? 1.5 : 0.8}
        strokeDasharray={active ? "none" : "3 3"}
        opacity={lineOpacity}
      />
      {active && (
        <circle r={2.5} fill={GOLD_LIGHT} filter="url(#glow-gold)">
          <animateMotion
            dur="1.2s"
            repeatCount="indefinite"
            path={`M${sx},${sy} L${ex},${ey}`}
          />
          <animate
            attributeName="opacity"
            values="1;0.3;1"
            dur="1.2s"
            repeatCount="indefinite"
          />
        </circle>
      )}
    </g>
  );
}

// ── Gold Checkmark ───────────────────────────────────────────────

function GoldCheck({ x, y, size = 7 }: { x: number; y: number; size?: number }) {
  const s = size;
  return (
    <g transform={`translate(${x - s}, ${y - s * 0.7})`}>
      <polyline
        points={`${s * 0.2},${s * 0.9} ${s * 0.75},${s * 1.4} ${s * 1.8},${s * 0.2}`}
        fill="none"
        stroke={GOLD_LIGHT}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </g>
  );
}

// ── Agent Node ───────────────────────────────────────────────────

function AgentNodeSvg({
  x, y, radius, label, status, isCenter = false, onClick,
}: {
  x: number; y: number; radius: number; label: string;
  status: AgentState["status"] | "thinking";
  isCenter?: boolean;
  onClick?: () => void;
}) {
  const isActive = status === "active" || status === "thinking";
  const isDone = status === "done";
  const color = isCenter
    ? (isActive ? GOLD_LIGHT : isDone ? GOLD_DONE : GOLD)
    : statusColor(status as AgentState["status"]);

  return (
    <g
      style={{ cursor: "pointer" }}
      onClick={onClick}
    >
      {/* Done: soft gold breathing pulse */}
      {isDone && (
        <circle cx={x} cy={y} r={radius} fill="none" stroke={GOLD_DONE} strokeWidth={1.2} opacity={0.5}>
          <animate attributeName="r" values={`${radius};${radius + 5};${radius}`} dur="3s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.5;0.15;0.5" dur="3s" repeatCount="indefinite" />
        </circle>
      )}

      {/* Active: radar ripples */}
      {isActive && Array.from({ length: 3 }, (_, i) => (
        <circle
          key={`ripple-${i}`}
          cx={x} cy={y} r={radius}
          fill="none" stroke={color} strokeWidth={1} opacity={0}
        >
          <animate
            attributeName="r"
            values={`${radius};${radius + 20}`}
            dur="2s" begin={`${i * 0.66}s`} repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            values="0.5;0"
            dur="2s" begin={`${i * 0.66}s`} repeatCount="indefinite"
          />
        </circle>
      ))}

      {/* Active glow */}
      {isActive && (
        <circle cx={x} cy={y} r={radius + 3} fill={color} opacity={0.25} filter="url(#glow-gold)">
          <animate attributeName="opacity" values="0.25;0.1;0.25" dur="2s" repeatCount="indefinite" />
        </circle>
      )}

      {/* Inner circle */}
      <circle
        cx={x} cy={y} r={radius}
        fill={NAVY}
        stroke={color}
        strokeWidth={isActive ? 2 : 1.2}
        opacity={1}
      />

      {/* Label or Check */}
      {isDone ? (
        <GoldCheck x={x} y={y} size={isCenter ? 9 : 7} />
      ) : (
        <text
          x={x} y={y + (isCenter ? 0 : 1)}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={isCenter ? 8 : 7}
          fontFamily="Georgia, serif"
          fontWeight={600}
          fill={color}
        >
          {label}
        </text>
      )}
    </g>
  );
}

// ── Progress Bar ─────────────────────────────────────────────────

function ProgressBar({ progress, detail }: { progress: number; detail: string }) {
  return (
    <div className="space-y-2">
      <div className="h-2 rounded-full overflow-hidden" style={{ background: "rgba(176,138,48,0.15)" }}>
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${progress}%`,
            background: "linear-gradient(90deg, #8a6d24, #b08a30, #c9a84c)",
          }}
        />
      </div>
      <div className="flex justify-between items-center">
        <span
          className="text-xs"
          style={{ color: "var(--color-text-muted)", fontFamily: "Georgia, serif" }}
        >
          {detail}
        </span>
        <span
          className="text-xs font-semibold"
          style={{ color: "var(--color-accent)", fontFamily: "Georgia, serif" }}
        >
          {progress}%
        </span>
      </div>
    </div>
  );
}

// ── Agent Detail Modal ──────────────────────────────────────────

function AgentModal({
  label,
  status,
  onClose,
}: {
  label: string;
  status: AgentState["status"] | "thinking";
  onClose: () => void;
}) {
  const role = AGENT_ROLES[label] ?? { title: label, description: "" };

  const statusLabels: Record<string, string> = {
    idle: "En espera",
    active: "Leyendo fallos...",
    thinking: "Sintetizando informe estrategico...",
    done: "Completado",
    error: "Error",
  };

  const statusLabel = statusLabels[status] ?? status;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(26, 26, 46, 0.6)", backdropFilter: "blur(4px)" }}
      onClick={onClose}
    >
      <div
        className="glass-card p-6 max-w-sm w-full mx-4 animate-slide-up"
        style={{ borderColor: "var(--color-border-active)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3
            className="text-base font-bold gold-text"
            style={{ fontFamily: "Georgia, serif" }}
          >
            {role.title}
          </h3>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full flex items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-accent)] hover:bg-[var(--color-accent-muted)] transition-all"
          >
            x
          </button>
        </div>

        {/* Status badge */}
        <div className="mb-4">
          <span
            className="text-xs px-3 py-1 rounded-full inline-block"
            style={{
              background:
                status === "done"
                  ? "var(--color-accent-muted)"
                  : status === "active" || status === "thinking"
                  ? "rgba(176, 138, 48, 0.15)"
                  : status === "error"
                  ? "var(--color-danger-bg)"
                  : "rgba(107, 104, 120, 0.1)",
              color:
                status === "done" || status === "active" || status === "thinking"
                  ? "var(--color-accent)"
                  : status === "error"
                  ? "var(--color-danger)"
                  : "var(--color-text-muted)",
              fontFamily: "Georgia, serif",
            }}
          >
            {statusLabel}
          </span>
        </div>

        {/* Description */}
        <div
          className="border-l-2 pl-3 text-sm leading-relaxed"
          style={{
            borderColor: "var(--color-accent)",
            color: "var(--color-text)",
            fontFamily: "Georgia, serif",
          }}
        >
          {role.description}
        </div>
      </div>
    </div>
  );
}

// ── Main Panel ───────────────────────────────────────────────────

export function AgentSwarmPanel({ swarmProgress }: { swarmProgress: SwarmProgress }) {
  const { step, progress, detail, agents, synthesizerActive } = swarmProgress;
  const [selectedAgent, setSelectedAgent] = useState<{
    label: string;
    status: AgentState["status"] | "thinking";
  } | null>(null);

  const agentPositions = useMemo(
    () => Array.from({ length: TOTAL_AGENTS }, (_, i) => ({ ...agentPos(i, TOTAL_AGENTS), id: i })),
    [],
  );

  const supervisorStatus = step === "done"
    ? "done"
    : synthesizerActive
      ? "thinking"
      : step === "search"
        ? "active"
        : agents.some((a) => a.status === "active")
          ? "active"
          : "idle";

  const centerLabel = synthesizerActive ? "OPUS" : "ORQ";

  const handleNodeClick = useCallback((label: string, status: AgentState["status"] | "thinking") => {
    setSelectedAgent({ label, status });
  }, []);

  return (
    <div
      className="glass-card p-5 space-y-4 animate-fade-in"
      style={{ borderColor: "var(--color-border-active)" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3
          className="text-sm font-semibold"
          style={{ color: "var(--color-accent)", fontFamily: "Georgia, serif" }}
        >
          {step === "done" ? "Analisis completo" : "Analizando jurisprudencia..."}
        </h3>
        <span
          className="text-xs px-2 py-0.5 rounded-full"
          style={{
            background: step === "done" ? "var(--color-accent-muted)" : "var(--color-accent-muted)",
            color: "var(--color-accent)",
            fontFamily: "Georgia, serif",
          }}
        >
          {step === "search" && "Buscando"}
          {step === "analyze" && "Leyendo fallos"}
          {step === "synthesize" && "Sintetizando"}
          {step === "done" && "Completado"}
        </span>
      </div>

      {/* SVG Graph with animated dots */}
      <div className="flex justify-center">
        <div className="relative" style={{ maxWidth: 320, maxHeight: 320, width: "100%" }}>
          <AnimatedDots />
          <svg
            width="100%"
            viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
            className="relative z-10"
          >
            <SvgDefs />

            {/* Orbit circle (subtle) */}
            <circle
              cx={CENTER} cy={CENTER} r={ORBIT_RADIUS}
              fill="none" stroke={GOLD_DIM} strokeWidth={0.5}
              strokeDasharray="4 4"
            />

            {/* Connection lines */}
            {agentPositions.map(({ x, y, id }) => {
              const agent = agents.find((a) => a.id === id);
              return (
                <ConnectionLine
                  key={`conn-${id}`}
                  x1={CENTER} y1={CENTER}
                  x2={x} y2={y}
                  active={agent?.status === "active"}
                  done={agent?.status === "done"}
                />
              );
            })}

            {/* Agent nodes */}
            {agentPositions.map(({ x, y, id }) => {
              const agent = agents.find((a) => a.id === id);
              const label = `L${id + 1}`;
              return (
                <AgentNodeSvg
                  key={`agent-${id}`}
                  x={x} y={y}
                  radius={NODE_R_AGENT}
                  label={label}
                  status={agent?.status ?? "idle"}
                  onClick={() => handleNodeClick(label, agent?.status ?? "idle")}
                />
              );
            })}

            {/* Center: Orchestrator / Synthesizer */}
            <AgentNodeSvg
              x={CENTER} y={CENTER}
              radius={NODE_R_CENTER}
              label={centerLabel}
              status={supervisorStatus}
              isCenter
              onClick={() => handleNodeClick(centerLabel, supervisorStatus)}
            />
          </svg>
        </div>
      </div>

      {/* Progress bar */}
      <ProgressBar progress={progress} detail={detail} />

      {/* Agent status summary — gold only, no green */}
      <div className="flex justify-center gap-4 text-xs" style={{ fontFamily: "Georgia, serif" }}>
        <span style={{ color: TEXT_MUTED }}>
          <span style={{ color: GOLD_DONE }}>&#10003;</span>{" "}
          {agents.filter((a) => a.status === "done").length} completados
        </span>
        <span style={{ color: TEXT_MUTED }}>
          <span style={{ color: GOLD_LIGHT }}>&#9679;</span>{" "}
          {agents.filter((a) => a.status === "active").length} leyendo
        </span>
        <span style={{ color: TEXT_MUTED }}>
          <span style={{ color: GOLD_DIM }}>&#9679;</span>{" "}
          {agents.filter((a) => a.status === "idle").length} en espera
        </span>
      </div>

      {/* Modal */}
      {selectedAgent && (
        <AgentModal
          label={selectedAgent.label}
          status={selectedAgent.status}
          onClose={() => setSelectedAgent(null)}
        />
      )}
    </div>
  );
}
