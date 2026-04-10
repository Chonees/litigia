"use client";

import { useState, useEffect, useRef } from "react";
import { useAnalysisStream } from "@/lib/use-analysis-stream";
import { AnalisisForm } from "@/components/forms";
import { AnalisisResult } from "@/components/results";
import { AgentSwarmPanel } from "@/components/agent-swarm";
import { SectionHeader, GoldButton } from "@/components/ui";
import { autoSave } from "@/lib/saved-items";
import { logUsage } from "@/lib/usage";

const COST_ESTIMATES: Record<string, { reader: number; synth: number }> = {
  premium:  { reader: 0.027, synth: 0.52 },  // Sonnet reader + Opus synth
  standard: { reader: 0.005, synth: 0.52 },  // Haiku reader + Opus synth
  economy:  { reader: 0.005, synth: 0.05 },  // Haiku reader + Sonnet synth
};

function estimateCost(tier: string, topK: number, transparency = false): number {
  const rates = COST_ESTIMATES[tier] || COST_ESTIMATES.premium;
  const readerCost = rates.reader * topK * (transparency ? 1.4 : 1);
  return readerCost + rates.synth;
}

export default function AnalisisPage() {
  const analysis = useAnalysisStream();
  const [lastQuery, setLastQuery] = useState("");
  const [lastTier, setLastTier] = useState("premium");
  const [lastTopK, setLastTopK] = useState(10);
  const savedRef = useRef(false);
  const [liveEstimate, setLiveEstimate] = useState("");

  // Warn before page reload/close if analysis is running
  useEffect(() => {
    function handleBeforeUnload(e: BeforeUnloadEvent) {
      if (analysis.isRunning) {
        analysis.abort();
        e.preventDefault();
      }
    }
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      // Abort on unmount (page navigation)
      if (analysis.isRunning) {
        analysis.abort();
      }
    };
  }, [analysis.isRunning, analysis.abort]);

  // Auto-save + log usage when result arrives
  useEffect(() => {
    if (analysis.result && !savedRef.current) {
      savedRef.current = true;
      const cost = analysis.result.cost as Record<string, unknown> | undefined;
      const tier = (cost?.tier as string) || lastTier;
      const tierLabel = tier === "premium" ? "Premium" : tier === "standard" ? "Standard" : "Economy";
      const costUsd = (cost?.total_cost_usd as number) || 0;
      const agentCount = (analysis.result.fallos_analizados as number) || 0;

      autoSave(
        "analisis",
        `[${tierLabel} · ${agentCount} agentes · $${costUsd.toFixed(2)}] ${lastQuery.slice(0, 60)}`,
        analysis.result,
        { descripcion_caso: lastQuery, tier, top_k: agentCount },
      );

      if (cost) {
        logUsage({
          tool: "analisis",
          tier,
          input_tokens: (cost.input_tokens as number) || 0,
          output_tokens: (cost.output_tokens as number) || 0,
          cost_usd: costUsd,
          reader_model: cost.reader_model as string,
          synth_model: cost.synth_model as string,
          fallos_analyzed: agentCount,
        }).catch(() => {});
      }
    }
  }, [analysis.result, lastQuery, lastTier]);

  function handleFormChange(e: React.FormEvent<HTMLFormElement>) {
    const formData = new FormData(e.currentTarget);
    const tier = formData.get("tier") as string || "premium";
    const topK = parseInt(formData.get("top_k") as string || "10");
    const transparency = formData.get("transparency") === "on";
    const est = estimateCost(tier, topK, transparency);
    setLiveEstimate(`Costo estimado: ~$${est.toFixed(2)} USD${transparency ? " (con transparencia)" : ""}`);
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const descripcion = (formData.get("descripcion") as string || "").trim().replace(/\s+/g, " ");
    const fuero = formData.get("fuero") as string;
    const tier = formData.get("tier") as string;
    const topK = parseInt(formData.get("top_k") as string || "10");
    const transparency = formData.get("transparency") === "on";

    // Safety: confirm before expensive runs
    const est = estimateCost(tier, topK, transparency);
    if (est > 1.0) {
      if (!confirm(`Este análisis costará aproximadamente $${est.toFixed(2)} USD. ¿Continuar?`)) {
        return;
      }
    }

    savedRef.current = false;
    setLastQuery(descripcion);
    setLastTier(tier);
    setLastTopK(topK);

    console.log(`[LITIGIA] Starting analysis: tier=${tier}, top_k=${topK}, transparency=${transparency}, est=$${est.toFixed(2)}`);
    analysis.startAnalysis(descripcion, fuero || undefined, tier, topK, transparency);
  }

  function handleCancel() {
    analysis.abort();
  }

  return (
    <div className="page-enter space-y-8">
      <form onSubmit={handleSubmit} onChange={handleFormChange} className="space-y-6">
        <SectionHeader label="Visual Intelligence" title="Análisis Predictivo" />
        <div className="animate-fade-in" style={{ animationDelay: "0.1s", animationFillMode: "both" }}>
          <AnalisisForm />
        </div>

        {/* Cost estimate + submit/cancel */}
        <div className="animate-fade-in space-y-3" style={{ animationDelay: "0.2s", animationFillMode: "both" }}>
          {liveEstimate && (
            <p className="text-[11px] text-center text-[var(--muted)]">{liveEstimate}</p>
          )}

          {analysis.isRunning ? (
            <button
              type="button"
              onClick={handleCancel}
              className="w-full py-3.5 bg-[var(--danger)] text-white font-semibold text-sm tracking-wide uppercase transition-all hover:opacity-90 active:scale-[0.98]"
            >
              ⏹ Detener Análisis
            </button>
          ) : (
            <GoldButton disabled={false}>
              Iniciar Análisis
            </GoldButton>
          )}
        </div>
      </form>

      {analysis.swarmProgress && (
        <AgentSwarmPanel swarmProgress={analysis.swarmProgress} />
      )}

      {analysis.error && (
        <div className="bg-[var(--danger-container)] border-l-2 border-[var(--danger)] p-4 animate-scale-in">
          <p className="text-sm text-[var(--danger)]">{analysis.error}</p>
        </div>
      )}

      {analysis.result && (
        <div className="animate-slide-up">
          <AnalisisResult data={analysis.result} />
        </div>
      )}
    </div>
  );
}
