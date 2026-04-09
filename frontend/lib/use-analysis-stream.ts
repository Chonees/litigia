"use client";

import { useState, useCallback, useRef } from "react";
import type { SwarmProgress, AgentState } from "@/components/agent-swarm";

const API_BASE = "http://localhost:8000/api/v1";
const CONCURRENCY = 10;

interface UseAnalysisStreamReturn {
  swarmProgress: SwarmProgress | null;
  result: Record<string, unknown> | null;
  error: string | null;
  isRunning: boolean;
  startAnalysis: (descripcion_caso: string, fuero?: string) => void;
}

function buildAgents(total: number): AgentState[] {
  return Array.from({ length: total }, (_, i) => ({ id: i, status: "idle" as const }));
}

/**
 * Hook that connects to the SSE streaming endpoint and
 * produces SwarmProgress updates for the AgentSwarmPanel.
 */
export function useAnalysisStream(): UseAnalysisStreamReturn {
  const [swarmProgress, setSwarmProgress] = useState<SwarmProgress | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const startAnalysis = useCallback((descripcion_caso: string, fuero?: string) => {
    // Abort any previous run
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setResult(null);
    setError(null);
    setIsRunning(true);

    const agents = buildAgents(CONCURRENCY);
    setSwarmProgress({
      step: "search",
      progress: 0,
      detail: "Iniciando analisis...",
      agents,
      synthesizerActive: false,
    });

    // SSE via fetch (EventSource doesn't support POST)
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/analisis/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ descripcion_caso, fuero }),
          signal: controller.signal,
        });

        if (!res.ok) throw new Error(`API error: ${res.status}`);
        if (!res.body) throw new Error("No response body");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let doneCount = 0;

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

              if (event.step === "search") {
                setSwarmProgress({
                  step: "search",
                  progress: 0,
                  detail: event.detail,
                  agents: buildAgents(CONCURRENCY),
                  synthesizerActive: false,
                });
              } else if (event.step === "analyze") {
                // Map progress to agent states
                const pct = event.progress ?? 0;
                const newDone = Math.floor((pct / 100) * CONCURRENCY);
                const newAgents: AgentState[] = buildAgents(CONCURRENCY).map((a) => {
                  if (a.id < doneCount) return { ...a, status: "done" as const };
                  // Active agents: the ones currently being processed
                  if (a.id < doneCount + Math.min(CONCURRENCY - doneCount, CONCURRENCY)) {
                    if (a.id < newDone) return { ...a, status: "done" as const };
                    return { ...a, status: "active" as const };
                  }
                  return a;
                });
                doneCount = newDone;

                setSwarmProgress({
                  step: "analyze",
                  progress: pct,
                  detail: event.detail,
                  agents: newAgents,
                  synthesizerActive: false,
                });
              } else if (event.step === "synthesize") {
                setSwarmProgress({
                  step: "synthesize",
                  progress: 100,
                  detail: event.detail,
                  agents: buildAgents(CONCURRENCY).map((a) => ({ ...a, status: "done" as const })),
                  synthesizerActive: true,
                });
              } else if (event.step === "done") {
                setSwarmProgress({
                  step: "done",
                  progress: 100,
                  detail: "Analisis completo",
                  agents: buildAgents(CONCURRENCY).map((a) => ({ ...a, status: "done" as const })),
                  synthesizerActive: false,
                });
                setResult(event.result ?? null);
                setIsRunning(false);
              }
            } catch {
              // Skip malformed JSON lines
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError((err as Error).message);
          setIsRunning(false);
        }
      }
    })();
  }, []);

  return { swarmProgress, result, error, isRunning, startAnalysis };
}
