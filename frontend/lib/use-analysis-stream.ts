"use client";

import { useState, useCallback, useRef } from "react";
import type { SwarmProgress, AgentState } from "@/components/agent-swarm";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002/api/v1";

interface UseAnalysisStreamReturn {
  swarmProgress: SwarmProgress | null;
  result: Record<string, unknown> | null;
  error: string | null;
  isRunning: boolean;
  startAnalysis: (descripcion_caso: string, fuero?: string, tier?: string, top_k?: number, transparency?: boolean) => void;
  abort: () => void;
}

export function useAnalysisStream(): UseAnalysisStreamReturn {
  const [swarmProgress, setSwarmProgress] = useState<SwarmProgress | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const agentsRef = useRef<AgentState[]>([]);
  const totalRef = useRef(0);
  const synthThinkingRef = useRef("");

  const startAnalysis = useCallback((descripcion_caso: string, fuero?: string, tier?: string, top_k?: number, transparency?: boolean) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setResult(null);
    setError(null);
    setIsRunning(true);
    agentsRef.current = [];
    totalRef.current = 0;

    setSwarmProgress({
      step: "search",
      progress: 0,
      detail: "Iniciando análisis...",
      agents: [],
      synthesizerActive: false,
      costUsd: 0,
      totalAgents: top_k || 100,
    });

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/analisis/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ descripcion_caso, fuero, tier: tier || "premium", top_k: top_k || 100, transparency: transparency || false }),
          signal: controller.signal,
        });

        if (!res.ok) throw new Error(`API error: ${res.status}`);
        if (!res.body) throw new Error("No response body");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const event = JSON.parse(jsonStr);
              const liveCost = event.cost_usd ?? 0;

              if (event.step === "error") {
                setError(event.detail || "Error de validación");
                setIsRunning(false);
                setSwarmProgress(null);
                return;
              } else if (event.step === "search") {
                setSwarmProgress({
                  step: "search",
                  progress: 0,
                  detail: event.detail,
                  agents: [],
                  synthesizerActive: false,
                  costUsd: 0,
                  totalAgents: totalRef.current || (top_k || 100),
                });
              } else if (event.step === "analyze" && event.total_agents) {
                // Initial analyze event — build agent array
                const total = event.total_agents;
                totalRef.current = total;
                agentsRef.current = Array.from({ length: total }, (_, i) => ({
                  id: i, status: "idle" as const,
                }));
                setSwarmProgress({
                  step: "analyze",
                  progress: 0,
                  detail: event.detail,
                  agents: [...agentsRef.current],
                  synthesizerActive: false,
                  costUsd: 0,
                  totalAgents: total,
                });
              } else if (event.step === "agent_event") {
                const id = event.agent_id as number;
                if (id === -1) {
                  // Synthesizer/Orchestrator event
                  synthThinkingRef.current = event.thinking || "";
                  setSwarmProgress(prev => prev ? {
                    ...prev,
                    synthesizerActive: event.status === "active",
                    synthThinking: event.thinking || "",
                    costUsd: liveCost,
                  } : null);
                } else {
                  // Per-agent status update (active/done/error)
                  const agents = agentsRef.current;
                  if (agents[id]) {
                    agents[id] = {
                      ...agents[id],
                      status: event.status,
                      thinking: event.thinking,
                      resultado: event.resultado,
                    };
                    agentsRef.current = agents;
                    setSwarmProgress(prev => prev ? {
                      ...prev,
                      agents: [...agents],
                      costUsd: liveCost,
                    } : null);
                  }
                }
              } else if (event.step === "analyze") {
                // Progress update
                setSwarmProgress(prev => prev ? {
                  ...prev,
                  step: "analyze",
                  progress: event.progress ?? prev.progress,
                  detail: event.detail,
                  agents: [...agentsRef.current],
                  costUsd: liveCost,
                } : null);
              } else if (event.step === "synthesize") {
                setSwarmProgress(prev => prev ? {
                  ...prev,
                  step: "synthesize",
                  progress: 100,
                  detail: event.detail,
                  agents: [...agentsRef.current],
                  synthesizerActive: true,
                  costUsd: liveCost,
                } : null);
              } else if (event.step === "cancelled") {
                setSwarmProgress(prev => prev ? {
                  ...prev,
                  step: "done",
                  detail: event.detail || "Análisis cancelado",
                  agents: [...agentsRef.current],
                  synthesizerActive: false,
                  costUsd: liveCost,
                } : null);
                setIsRunning(false);
              } else if (event.step === "done") {
                setSwarmProgress(prev => prev ? {
                  ...prev,
                  step: "done",
                  progress: 100,
                  detail: "Análisis completo",
                  agents: [...agentsRef.current],
                  synthesizerActive: false,
                  costUsd: liveCost,
                } : null);
                setResult(event.result ?? null);
                setIsRunning(false);
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setSwarmProgress(prev => prev ? { ...prev, detail: "Análisis cancelado por el usuario" } : null);
        } else {
          setError((err as Error).message);
        }
        setIsRunning(false);
      }
    })();
  }, []);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setIsRunning(false);
  }, []);

  return { swarmProgress, result, error, isRunning, startAnalysis, abort };
}
