"use client";

import { useState } from "react";
import {
  searchJurisprudencia,
  generateEscrito,
  resumirFallo,
  generateOficio,
} from "@/lib/api";
import { useAnalysisStream } from "@/lib/use-analysis-stream";
import { ToolSelector, type Tool } from "@/components/tool-selector";
import {
  JurisprudenciaForm,
  EscritoForm,
  ResumenForm,
  OficioForm,
  AnalisisForm,
} from "@/components/forms";
import {
  JurisprudenciaResult,
  EscritoResult,
  ResumenResult,
  OficioResult,
  AnalisisResult,
} from "@/components/results";
import { AgentSwarmPanel } from "@/components/agent-swarm";

const TOOL_TITLES: Record<Tool, string> = {
  jurisprudencia: "Buscar Jurisprudencia",
  escrito: "Generar Escrito Judicial",
  resumen: "Resumir Fallo",
  oficio: "Generar Oficio",
  analisis: "Analisis Predictivo",
};

export default function Home() {
  const [activeTool, setActiveTool] = useState<Tool>("jurisprudencia");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Streaming analysis hook
  const analysis = useAnalysisStream();

  function handleToolChange(tool: Tool) {
    setActiveTool(tool);
    setResult(null);
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data = Object.fromEntries(formData.entries()) as Record<string, string>;

    // Analysis uses streaming — different path
    if (activeTool === "analisis") {
      setResult(null);
      setError(null);
      analysis.startAnalysis(data.descripcion, data.fuero || undefined);
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let res;
      switch (activeTool) {
        case "jurisprudencia":
          res = await searchJurisprudencia({
            descripcion_caso: data.descripcion,
            jurisdiccion: data.jurisdiccion || undefined,
            fuero: data.fuero || undefined,
            top_k: parseInt(data.top_k || "5"),
          });
          break;
        case "escrito":
          res = await generateEscrito({
            tipo: data.tipo,
            fuero: data.fuero,
            tema: data.tema,
            posicion: data.posicion,
            jurisdiccion: data.jurisdiccion,
            datos_caso: data.datos_caso,
          });
          break;
        case "resumen":
          res = await resumirFallo(data.texto_fallo);
          break;
        case "oficio":
          res = await generateOficio({
            destinatario: data.destinatario,
            motivo: data.motivo,
            datos_expediente: data.datos_expediente,
            datos_requeridos: data.datos_requeridos,
          });
          break;
      }
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de conexion con el servidor");
    } finally {
      setLoading(false);
    }
  }

  const isAnalysisActive = activeTool === "analisis";
  const isLoading = isAnalysisActive ? analysis.isRunning : loading;
  const displayError = isAnalysisActive ? analysis.error : error;
  const displayResult = isAnalysisActive ? analysis.result : result;

  return (
    <div className="space-y-6">
      <ToolSelector active={activeTool} onChange={handleToolChange} />

      <form
        onSubmit={handleSubmit}
        className="glass-card p-6 space-y-5"
      >
        <h2 className="text-lg font-bold gold-text pb-3 border-b border-[var(--color-border)]">
          {TOOL_TITLES[activeTool]}
        </h2>

        <div className="animate-fade-in" key={activeTool}>
          {activeTool === "jurisprudencia" && <JurisprudenciaForm />}
          {activeTool === "escrito" && <EscritoForm />}
          {activeTool === "resumen" && <ResumenForm />}
          {activeTool === "oficio" && <OficioForm />}
          {activeTool === "analisis" && <AnalisisForm />}
        </div>

        <button
          type="submit"
          disabled={isLoading}
          style={{ transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)" }}
          className="w-full py-3.5 bg-[var(--color-primary)] text-white rounded-xl font-semibold border border-[var(--color-accent)] shadow-lg shadow-amber-900/10 hover:shadow-xl hover:shadow-amber-900/15 hover:border-[var(--color-accent-light)] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <span className="animate-pulse-slow">Procesando...</span>
          ) : (
            "Enviar"
          )}
        </button>
      </form>

      {/* Agent Swarm Panel — only for analysis, while running */}
      {isAnalysisActive && analysis.swarmProgress && (
        <AgentSwarmPanel swarmProgress={analysis.swarmProgress} />
      )}

      {displayError && (
        <div className="glass-card p-4 border-[var(--color-danger)]/20 animate-slide-up">
          <p className="text-sm text-[var(--color-danger)]">{displayError}</p>
        </div>
      )}

      {displayResult && (
        <div className="glass-card p-6 animate-slide-up">
          <h3 className="text-lg font-bold gold-text pb-3 mb-4 border-b border-[var(--color-border)]">
            Resultado
          </h3>
          {activeTool === "jurisprudencia" && <JurisprudenciaResult data={displayResult} />}
          {activeTool === "escrito" && <EscritoResult data={displayResult} />}
          {activeTool === "resumen" && <ResumenResult data={displayResult} />}
          {activeTool === "oficio" && <OficioResult data={displayResult} />}
          {activeTool === "analisis" && <AnalisisResult data={displayResult} />}
        </div>
      )}
    </div>
  );
}
