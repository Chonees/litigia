"use client";

import { useState } from "react";
import { useAnalysisStream } from "@/lib/use-analysis-stream";
import { AnalisisForm } from "@/components/forms";
import { AnalisisResult } from "@/components/results";
import { AgentSwarmPanel } from "@/components/agent-swarm";
import { SectionHeader, GoldButton } from "@/components/ui";

export default function AnalisisPage() {
  const analysis = useAnalysisStream();
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data = Object.fromEntries(formData.entries()) as Record<string, string>;
    setError(null);
    analysis.startAnalysis(data.descripcion, data.fuero || undefined);
  }

  const displayError = analysis.error || error;

  return (
    <div className="space-y-8">
      <form onSubmit={handleSubmit} className="space-y-6">
        <SectionHeader label="Visual Intelligence" title="Análisis Predictivo" />
        <AnalisisForm />
        <GoldButton disabled={analysis.isRunning}>
          {analysis.isRunning ? <span className="animate-pulse-slow">Procesando...</span> : "Iniciar Análisis"}
        </GoldButton>
      </form>

      {analysis.swarmProgress && (
        <AgentSwarmPanel swarmProgress={analysis.swarmProgress} />
      )}

      {displayError && (
        <div className="bg-[var(--danger-container)]/10 border-l-2 border-[var(--danger)] p-4 animate-slide-up">
          <p className="text-sm text-[var(--danger)]">{displayError}</p>
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
