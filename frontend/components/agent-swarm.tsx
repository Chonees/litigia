"use client";

import { useEffect, useRef, useState, useMemo, useCallback } from "react";
import { colors } from "@/lib/tokens";

// ── Types ────────────────────────────────────────────────────────

export interface AgentState {
  id: number;
  status: "idle" | "active" | "done" | "error";
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

const GOLD = "#9A7B2D";
const GOLD_LIGHT = "#B08A30";
const GOLD_DIM = "rgba(176, 138, 48, 0.2)";
const GOLD_DONE = "#B08A30";
const SURFACE = "#FFFFFF";
const DANGER = "#C62828";

const AGENT_ROLES: Record<string, { title: string; description: string }> = {
  ORQ: {
    title: "Orquestador",
    description: "Coordina el pipeline completo. Distribuye los fallos entre los lectores, monitorea el progreso y lanza al sintetizador cuando todos terminan.",
  },
  OPUS: {
    title: "Sintetizador (Opus)",
    description: "Recibe los 100 análisis estructurados y cruza patrones: estrategias exitosas vs fracasadas, normas más citadas, precedentes clave, riesgos concretos.",
  },
};

for (let i = 0; i < TOTAL_AGENTS; i++) {
  AGENT_ROLES[`L${i + 1}`] = {
    title: `Lector ${i + 1}`,
    description: `Lee ~10 fallos asignados. Extrae resultado, normas, precedentes, vía procesal, doctrina, hechos determinantes, prueba decisiva, quantum y relevancia.`,
  };
}

// ── Helpers ──────────────────────────────────────────────────────

function agentPos(index: number, total: number) {
  const angle = (index * 2 * Math.PI) / total - Math.PI / 2;
  return { x: CENTER + ORBIT_RADIUS * Math.cos(angle), y: CENTER + ORBIT_RADIUS * Math.sin(angle) };
}

function statusColor(status: AgentState["status"]) {
  if (status === "active") return GOLD_LIGHT;
  if (status === "done") return GOLD_DONE;
  if (status === "error") return DANGER;
  return GOLD_DIM;
}

// ── Animated Dot Background ─────────────────────────────────────

interface Dot { x: number; y: number; vx: number; vy: number }

function AnimatedDots() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dotsRef = useRef<Dot[]>([]);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = SVG_SIZE;
    canvas.height = SVG_SIZE;

    if (dotsRef.current.length === 0) {
      dotsRef.current = Array.from({ length: 60 }, () => ({
        x: Math.random() * SVG_SIZE,
        y: Math.random() * SVG_SIZE,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
      }));
    }

    function animate() {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, SVG_SIZE, SVG_SIZE);
      for (const dot of dotsRef.current) {
        dot.x += dot.vx; dot.y += dot.vy;
        if (dot.x < 0) dot.x = SVG_SIZE; if (dot.x > SVG_SIZE) dot.x = 0;
        if (dot.y < 0) dot.y = SVG_SIZE; if (dot.y > SVG_SIZE) dot.y = 0;
        ctx.beginPath(); ctx.arc(dot.x, dot.y, 1, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(154, 123, 45, 0.25)"; ctx.fill();
      }
      for (let i = 0; i < dotsRef.current.length; i++) {
        for (let j = i + 1; j < dotsRef.current.length; j++) {
          const a = dotsRef.current[i], b = dotsRef.current[j];
          const dist = Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
          if (dist < 50) {
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(154, 123, 45, ${0.12 * (1 - dist / 50)})`;
            ctx.lineWidth = 0.5; ctx.stroke();
          }
        }
      }
      animRef.current = requestAnimationFrame(animate);
    }
    animate();
    return () => cancelAnimationFrame(animRef.current);
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" style={{ width: "100%", height: "100%" }} />;
}

// ── SVG Components ───────────────────────────────────────────────

function SvgDefs() {
  return (
    <defs>
      <filter id="glow-gold" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="4" result="blur" />
        <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
    </defs>
  );
}

function ConnectionLine({ x1, y1, x2, y2, active, done }: { x1: number; y1: number; x2: number; y2: number; active: boolean; done: boolean }) {
  const dx = x2 - x1, dy = y2 - y1, dist = Math.sqrt(dx * dx + dy * dy);
  const ux = dx / dist, uy = dy / dist;
  const sx = x1 + ux * (NODE_R_CENTER + 4), sy = y1 + uy * (NODE_R_CENTER + 4);
  const ex = x2 - ux * (NODE_R_AGENT + 4), ey = y2 - uy * (NODE_R_AGENT + 4);

  return (
    <g>
      <line x1={sx} y1={sy} x2={ex} y2={ey} stroke={done ? GOLD_DONE : active ? GOLD : GOLD_DIM} strokeWidth={active ? 1.5 : 0.8} strokeDasharray={active ? "none" : "3 3"} opacity={done ? 0.5 : active ? 0.8 : 0.2} />
      {active && (
        <circle r={2.5} fill={GOLD_LIGHT} filter="url(#glow-gold)">
          <animateMotion dur="1.2s" repeatCount="indefinite" path={`M${sx},${sy} L${ex},${ey}`} />
          <animate attributeName="opacity" values="1;0.3;1" dur="1.2s" repeatCount="indefinite" />
        </circle>
      )}
    </g>
  );
}

function GoldCheck({ x, y, size = 7 }: { x: number; y: number; size?: number }) {
  return (
    <g transform={`translate(${x - size}, ${y - size * 0.7})`}>
      <polyline points={`${size * 0.2},${size * 0.9} ${size * 0.75},${size * 1.4} ${size * 1.8},${size * 0.2}`} fill="none" stroke={GOLD_LIGHT} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </g>
  );
}

function AgentNodeSvg({ x, y, radius, label, status, isCenter = false, onClick }: { x: number; y: number; radius: number; label: string; status: AgentState["status"] | "thinking"; isCenter?: boolean; onClick?: () => void }) {
  const isActive = status === "active" || status === "thinking";
  const isDone = status === "done";
  const color = isCenter ? (isActive ? GOLD_LIGHT : isDone ? GOLD_DONE : GOLD) : statusColor(status as AgentState["status"]);

  return (
    <g style={{ cursor: "pointer" }} onClick={onClick}>
      {isDone && (
        <circle cx={x} cy={y} r={radius} fill="none" stroke={GOLD_DONE} strokeWidth={1.2} opacity={0.5}>
          <animate attributeName="r" values={`${radius};${radius + 5};${radius}`} dur="3s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.5;0.15;0.5" dur="3s" repeatCount="indefinite" />
        </circle>
      )}
      {isActive && Array.from({ length: 3 }, (_, i) => (
        <circle key={i} cx={x} cy={y} r={radius} fill="none" stroke={color} strokeWidth={1} opacity={0}>
          <animate attributeName="r" values={`${radius};${radius + 20}`} dur="2s" begin={`${i * 0.66}s`} repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.5;0" dur="2s" begin={`${i * 0.66}s`} repeatCount="indefinite" />
        </circle>
      ))}
      {isActive && (
        <circle cx={x} cy={y} r={radius + 3} fill={color} opacity={0.25} filter="url(#glow-gold)">
          <animate attributeName="opacity" values="0.25;0.1;0.25" dur="2s" repeatCount="indefinite" />
        </circle>
      )}
      <circle cx={x} cy={y} r={radius} fill={SURFACE} stroke={color} strokeWidth={isActive ? 2 : 1.2} />
      {isDone ? <GoldCheck x={x} y={y} size={isCenter ? 9 : 7} /> : (
        <text x={x} y={y + (isCenter ? 0 : 1)} textAnchor="middle" dominantBaseline="central" fontSize={isCenter ? 8 : 7} fontFamily="'Inter', sans-serif" fontWeight={600} fill={color}>{label}</text>
      )}
    </g>
  );
}

// ── Progress Bar ─────────────────────────────────────────────────

function ProgressBar({ progress, detail }: { progress: number; detail: string }) {
  return (
    <div className="space-y-2">
      <div className="h-1 overflow-hidden" style={{ background: "var(--container)" }}>
        <div className="h-full gold-gradient transition-all duration-500 ease-out" style={{ width: `${progress}%` }} />
      </div>
      <div className="flex justify-between items-center">
        <span className="text-[11px] text-[var(--muted)]">{detail}</span>
        <span className="text-[11px] font-semibold text-[var(--primary)]">{progress}%</span>
      </div>
    </div>
  );
}

// ── Agent Modal ──────────────────────────────────────────────────

function AgentModal({ label, status, onClose }: { label: string; status: AgentState["status"] | "thinking"; onClose: () => void }) {
  const role = AGENT_ROLES[label] ?? { title: label, description: "" };
  const statusLabels: Record<string, string> = { idle: "En espera", active: "Leyendo fallos...", thinking: "Sintetizando informe...", done: "Completado", error: "Error" };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(26, 26, 26, 0.3)", backdropFilter: "blur(8px)" }} onClick={onClose}>
      <div className="bg-[var(--container-high)] border border-[var(--outline-variant)] p-6 max-w-sm w-full mx-4 animate-slide-up" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-heading text-base font-bold text-[var(--primary)]">{role.title}</h3>
          <button onClick={onClose} className="w-7 h-7 flex items-center justify-center text-[var(--muted)] hover:text-[var(--primary)] transition-colors">×</button>
        </div>
        <div className="mb-4">
          <span className="text-[11px] px-3 py-1 tracking-wide uppercase" style={{
            background: status === "done" || status === "active" || status === "thinking" ? "var(--color-accent-muted)" : status === "error" ? "var(--color-danger-bg)" : "var(--container)",
            color: status === "done" || status === "active" || status === "thinking" ? "var(--primary)" : status === "error" ? "var(--danger)" : "var(--muted)",
          }}>
            {statusLabels[status] ?? status}
          </span>
        </div>
        <div className="border-l-2 border-[var(--primary)] pl-3 text-sm leading-relaxed text-[var(--on-surface-variant)]">
          {role.description}
        </div>
      </div>
    </div>
  );
}

// ── Main Panel ───────────────────────────────────────────────────

export function AgentSwarmPanel({ swarmProgress }: { swarmProgress: SwarmProgress }) {
  const { step, progress, detail, agents, synthesizerActive } = swarmProgress;
  const [selectedAgent, setSelectedAgent] = useState<{ label: string; status: AgentState["status"] | "thinking" } | null>(null);

  const agentPositions = useMemo(
    () => Array.from({ length: TOTAL_AGENTS }, (_, i) => ({ ...agentPos(i, TOTAL_AGENTS), id: i })),
    [],
  );

  const supervisorStatus = step === "done" ? "done" : synthesizerActive ? "thinking" : step === "search" ? "active" : agents.some((a) => a.status === "active") ? "active" : "idle";
  const centerLabel = synthesizerActive ? "OPUS" : "ORQ";
  const handleNodeClick = useCallback((label: string, status: AgentState["status"] | "thinking") => { setSelectedAgent({ label, status }); }, []);

  return (
    <div className="bg-[var(--container-high)] p-5 space-y-4 animate-fade-in border border-[var(--outline-variant)]/30">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] font-semibold tracking-[0.15em] uppercase text-[var(--primary)]">
          {step === "done" ? "Análisis completo" : "Analizando jurisprudencia..."}
        </h3>
        <span className="text-[11px] px-3 py-1 tracking-wide uppercase bg-[var(--container)] text-[var(--primary)]">
          {step === "search" && "Buscando"}
          {step === "analyze" && "Leyendo fallos"}
          {step === "synthesize" && "Sintetizando"}
          {step === "done" && "Completado"}
        </span>
      </div>

      <div className="flex justify-center">
        <div className="relative" style={{ maxWidth: 320, maxHeight: 320, width: "100%" }}>
          <AnimatedDots />
          <svg width="100%" viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`} className="relative z-10">
            <SvgDefs />
            <circle cx={CENTER} cy={CENTER} r={ORBIT_RADIUS} fill="none" stroke={GOLD_DIM} strokeWidth={0.5} strokeDasharray="4 4" />
            {agentPositions.map(({ x, y, id }) => {
              const agent = agents.find((a) => a.id === id);
              return <ConnectionLine key={`c-${id}`} x1={CENTER} y1={CENTER} x2={x} y2={y} active={agent?.status === "active"} done={agent?.status === "done"} />;
            })}
            {agentPositions.map(({ x, y, id }) => {
              const agent = agents.find((a) => a.id === id);
              const label = `L${id + 1}`;
              return <AgentNodeSvg key={`a-${id}`} x={x} y={y} radius={NODE_R_AGENT} label={label} status={agent?.status ?? "idle"} onClick={() => handleNodeClick(label, agent?.status ?? "idle")} />;
            })}
            <AgentNodeSvg x={CENTER} y={CENTER} radius={NODE_R_CENTER} label={centerLabel} status={supervisorStatus} isCenter onClick={() => handleNodeClick(centerLabel, supervisorStatus)} />
          </svg>
        </div>
      </div>

      <ProgressBar progress={progress} detail={detail} />

      <div className="flex justify-center gap-6 text-[11px] text-[var(--muted)]">
        <span><span style={{ color: GOLD_DONE }}>✓</span> {agents.filter((a) => a.status === "done").length} completados</span>
        <span><span style={{ color: GOLD_LIGHT }}>●</span> {agents.filter((a) => a.status === "active").length} leyendo</span>
        <span><span style={{ color: GOLD_DIM }}>●</span> {agents.filter((a) => a.status === "idle").length} en espera</span>
      </div>

      {selectedAgent && <AgentModal label={selectedAgent.label} status={selectedAgent.status} onClose={() => setSelectedAgent(null)} />}
    </div>
  );
}
