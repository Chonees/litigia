"use client";

import { useState } from "react";
import {
  searchJurisprudencia,
  generateEscrito,
  resumirFallo,
  generateOficio,
  analisisPredictivo,
} from "@/lib/api";
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

  function handleToolChange(tool: Tool) {
    setActiveTool(tool);
    setResult(null);
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData(e.currentTarget);
    const data = Object.fromEntries(formData.entries()) as Record<string, string>;

    try {
      let res;
      switch (activeTool) {
        case "jurisprudencia":
          res = await searchJurisprudencia({
            descripcion_caso: data.descripcion,
            jurisdiccion: data.jurisdiccion || undefined,
            fuero: data.fuero || undefined,
            top_k: 5,
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
        case "analisis":
          res = await analisisPredictivo({
            descripcion_caso: data.descripcion,
            fuero: data.fuero || undefined,
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

  return (
    <div className="space-y-6">
      <ToolSelector active={activeTool} onChange={handleToolChange} />

      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-xl shadow-sm border border-[var(--color-border)] p-6 space-y-5"
      >
        <h2 className="text-lg font-bold text-[var(--color-primary)] pb-3 border-b border-[var(--color-border)]">
          {TOOL_TITLES[activeTool]}
        </h2>

        {activeTool === "jurisprudencia" && <JurisprudenciaForm />}
        {activeTool === "escrito" && <EscritoForm />}
        {activeTool === "resumen" && <ResumenForm />}
        {activeTool === "oficio" && <OficioForm />}
        {activeTool === "analisis" && <AnalisisForm />}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-[var(--color-primary)] text-white rounded-lg font-semibold hover:bg-[var(--color-primary-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-pulse-slow">Procesando con IA...</span>
            </span>
          ) : (
            "Enviar"
          )}
        </button>
      </form>

      {error && (
        <div className="bg-[var(--color-danger-bg)] border border-red-200 text-[var(--color-danger)] px-5 py-3 rounded-lg text-sm animate-slide-up">
          {error}
        </div>
      )}

      {result && (
        <div className="bg-white rounded-xl shadow-sm border border-[var(--color-border)] p-6">
          <h3 className="text-lg font-bold text-[var(--color-primary)] pb-3 mb-4 border-b border-[var(--color-border)]">
            Resultado
          </h3>
          {activeTool === "jurisprudencia" && <JurisprudenciaResult data={result} />}
          {activeTool === "escrito" && <EscritoResult data={result} />}
          {activeTool === "resumen" && <ResumenResult data={result} />}
          {activeTool === "oficio" && <OficioResult data={result} />}
          {activeTool === "analisis" && <AnalisisResult data={result} />}
        </div>
      )}
    </div>
  );
}
