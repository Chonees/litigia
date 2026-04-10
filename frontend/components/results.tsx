"use client";

import { useState } from "react";
import { downloadDocx } from "@/lib/api";
import { Card, CardHeader, StatBox } from "@/components/ui";

/* ═══════════════════════════════════════════════════════════════════
   Jurisprudencia
   ═══════════════════════════════════════════════════════════════════ */

export function JurisprudenciaResult({ data }: { data: Record<string, unknown> }) {
  const fallos = (data.fallos ?? []) as Array<{
    tribunal: string; fecha: string; caratula: string; resumen: string;
    argumento_clave: string; cita_textual: string; score: number;
    texto_completo: string; materia: string; fuente: string;
  }>;
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="space-y-3 animate-slide-up">
      <div className="flex items-center justify-between text-xs text-[var(--muted)] pb-3 border-b border-[var(--outline-variant)]/30">
        <span>{(data.total_encontrados as number) ?? 0} fallos encontrados</span>
      </div>

      {fallos.map((fallo, i) => (
        <div key={i} className="bg-[var(--container-high)] border-l-2 border-l-[var(--primary)] p-5 hover:bg-[var(--container-highest)] transition-colors">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h4 className="font-heading font-bold text-[var(--primary)] text-sm leading-tight">
                {fallo.caratula || "Sin carátula"}
              </h4>
              <div className="flex items-center gap-2 mt-1 text-[10px] tracking-wide uppercase text-[var(--muted)]">
                {fallo.tribunal && <span>{fallo.tribunal}</span>}
                {fallo.tribunal && fallo.fecha && <span>|</span>}
                {fallo.fecha && <span>{fallo.fecha}</span>}
                {fallo.materia && <><span>|</span><span>{fallo.materia}</span></>}
              </div>
            </div>
            <div className="px-3 py-1 bg-[var(--container)] text-[var(--primary)] text-xs font-bold font-heading">
              {(fallo.score * 100).toFixed(0)}%
            </div>
          </div>

          {fallo.resumen && (
            <p className="mt-3 text-sm text-[var(--on-surface-variant)] leading-relaxed">{fallo.resumen}</p>
          )}

          {fallo.argumento_clave && fallo.argumento_clave !== fallo.caratula && (
            <div className="mt-3 pl-3 border-l-2 border-l-[var(--outline-variant)]">
              <span className="text-[10px] font-semibold tracking-wide uppercase text-[var(--primary)]">Argumento clave</span>
              <p className="text-sm mt-0.5 text-[var(--on-surface-variant)]">{fallo.argumento_clave}</p>
            </div>
          )}

          {fallo.cita_textual && (
            <blockquote className="mt-3 text-sm italic border-l-2 border-[var(--primary-container)] pl-3 text-[var(--muted)] font-heading">
              &ldquo;{fallo.cita_textual}&rdquo;
            </blockquote>
          )}

          <div className="mt-3">
            {fallo.texto_completo && (
              <button
                onClick={() => setExpanded(expanded === i ? null : i)}
                className="text-[11px] font-semibold tracking-wide uppercase text-[var(--primary)] hover:text-[var(--secondary)] transition-colors"
              >
                {expanded === i ? "Ocultar texto completo" : "Ver texto completo"}
              </button>
            )}
          </div>
          {expanded === i && fallo.texto_completo && (
            <div className="mt-3 p-4 bg-[var(--container-lowest)] max-h-[500px] overflow-y-auto custom-scrollbar">
              <pre className="whitespace-pre-wrap font-heading text-xs leading-relaxed text-[var(--on-surface-variant)]">
                {fallo.texto_completo}
              </pre>
            </div>
          )}
        </div>
      ))}

      {fallos.length === 0 && (
        <div className="text-center py-12 text-[var(--muted)]">
          No se encontraron fallos relevantes para este caso.
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Escrito
   ═══════════════════════════════════════════════════════════════════ */

export function EscritoResult({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="space-y-4 animate-slide-up">
      <div className="bg-[var(--container-lowest)] p-6 max-h-[600px] overflow-y-auto custom-scrollbar">
        <pre className="whitespace-pre-wrap font-heading text-sm leading-relaxed text-[var(--on-surface)]">
          {data.contenido_texto as string}
        </pre>
      </div>
      <div className="flex items-center gap-4">
        {!!data.archivo_docx_base64 && (
          <button
            onClick={() => downloadDocx(data.archivo_docx_base64 as string, "escrito_litigia.docx")}
            className="px-6 py-2.5 border border-[var(--primary-container)] text-[var(--primary)] font-semibold text-xs tracking-wide uppercase hover:bg-[var(--primary)]/10 transition-all"
          >
            Descargar .docx
          </button>
        )}
        {((data.jurisprudencia_citada as unknown[]) ?? []).length > 0 && (
          <span className="text-[11px] text-[var(--muted)]">
            {(data.jurisprudencia_citada as unknown[]).length} fallos citados
          </span>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Resumen
   ═══════════════════════════════════════════════════════════════════ */

export function ResumenResult({ data }: { data: Record<string, unknown> }) {
  const sections = [
    { key: "hechos", label: "Hechos" },
    { key: "cuestion_juridica", label: "Cuestión Jurídica" },
    { key: "argumentos_actor", label: "Argumentos del Actor" },
    { key: "argumentos_demandado", label: "Argumentos del Demandado" },
    { key: "resolucion", label: "Resolución" },
    { key: "doctrina_aplicada", label: "Doctrina Aplicada" },
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      {sections.map(({ key, label }) => (
        <Card key={key} accent="gold">
          <CardHeader>{label}</CardHeader>
          <p className="text-sm leading-relaxed text-[var(--on-surface-variant)]">{data[key] as string}</p>
        </Card>
      ))}
      {(data.articulos_citados as string[])?.length > 0 && (
        <Card>
          <CardHeader>Artículos Citados</CardHeader>
          <div className="flex flex-wrap gap-2">
            {(data.articulos_citados as string[]).map((art, i) => (
              <span key={i} className="px-2 py-1 bg-[var(--container)] text-[var(--primary)] text-[11px] tracking-wide">
                {art}
              </span>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Oficio
   ═══════════════════════════════════════════════════════════════════ */

export function OficioResult({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="animate-slide-up">
      <div className="bg-[var(--container-lowest)] p-6">
        <pre className="whitespace-pre-wrap font-heading text-sm leading-relaxed text-[var(--on-surface)]">
          {(data as { contenido?: string }).contenido}
        </pre>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Análisis Predictivo
   ═══════════════════════════════════════════════════════════════════ */

interface FalloDetalle {
  caratula: string; tribunal: string; fecha: string; resultado: string;
  normas_citadas: string[]; precedentes_citados: string[]; via_procesal: string;
  doctrina_aplicada: string; hechos_determinantes: string; prueba_decisiva: string;
  quantum: string; votos: string; estrategia: string; argumento_clave: string;
  razon_resultado: string; relevancia_cliente: string; score: number; source_id: string;
  agent_thinking: string; reasoning: string;
}

const RESULTADO_CONFIG: Record<string, { label: string; color: string }> = {
  favorable: { label: "Favorable", color: "var(--primary)" },
  desfavorable: { label: "Desfavorable", color: "var(--danger)" },
  parcial: { label: "Parcial", color: "var(--muted)" },
  inadmisible: { label: "Inadmisible", color: "var(--muted)" },
};

function generateTransparencyPDF(data: Record<string, unknown>, fallos: FalloDetalle[]) {
  const cost = data.cost as Record<string, unknown> | undefined;
  const recomendacion = (data.recomendacion_estrategica as string) ?? "";
  const patronFav = (data.patron_factico_favorable as string) ?? "";
  const patronDesfav = (data.patron_factico_desfavorable as string) ?? "";
  const totalAnalyzed = (data.fallos_analizados as number) ?? 0;
  const favorables = (data.favorables as number) ?? 0;
  const desfavorables = (data.desfavorables as number) ?? 0;
  const inadmisibles = (data.inadmisibles as number) ?? 0;
  const parciales = (data.parciales as number) ?? 0;
  const pct = (data.porcentaje_favorable as number) ?? 0;

  const agentSections = fallos.map((f, i) => {
    const reasoning = f.reasoning || buildAgentNarrative(f);
    return `
      <div class="agent">
        <h3>Agente #${i + 1} — ${f.caratula}</h3>
        <p class="meta">${f.tribunal} | ${f.fecha} | <strong>${f.resultado.toUpperCase()}</strong></p>
        <div class="reasoning">${reasoning.replace(/\n/g, "<br>")}</div>
      </div>`;
  }).join("\n");

  const synthNarrative = `
    <p>Analicé ${totalAnalyzed} fallos. De los que entraron al fondo: ${favorables} favorables, ${desfavorables} desfavorables${parciales > 0 ? `, ${parciales} parciales` : ""}. ${inadmisibles > 0 ? `${inadmisibles} fueron inadmisibles (rechazados sin entrar al fondo).` : ""} Porcentaje favorable (excluyendo inadmisibles): ${pct.toFixed(0)}%.</p>
    ${patronFav ? `<p><strong>Patrón de los que ganaron:</strong> ${patronFav}</p>` : ""}
    ${patronDesfav ? `<p><strong>Patrón de los que perdieron:</strong> ${patronDesfav}</p>` : ""}
    ${recomendacion ? `<p><strong>Recomendación estratégica:</strong> ${recomendacion}</p>` : ""}`;

  const html = `<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>LITIGIA — Informe de Transparencia</title>
<style>
  body { font-family: 'Georgia', serif; max-width: 800px; margin: 0 auto; padding: 40px; color: #1a1a1a; line-height: 1.6; }
  h1 { color: #9A7B2D; border-bottom: 2px solid #9A7B2D; padding-bottom: 8px; font-size: 22px; }
  h2 { color: #9A7B2D; font-size: 16px; margin-top: 32px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
  h3 { font-size: 14px; color: #333; margin-bottom: 4px; }
  .meta { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .reasoning { font-size: 13px; background: #f9f9f7; border-left: 3px solid #9A7B2D; padding: 12px 16px; margin-bottom: 24px; }
  .agent { page-break-inside: avoid; margin-bottom: 20px; }
  .synth { font-size: 13px; background: #f5f3ee; padding: 16px; border: 1px solid #e0ddd5; }
  .footer { margin-top: 40px; text-align: center; font-size: 11px; color: #999; border-top: 1px solid #ddd; padding-top: 12px; }
  @media print { body { padding: 20px; } }
</style>
</head><body>
<h1>LITIGIA — Informe de Transparencia de Análisis</h1>
<p style="font-size:12px;color:#666;">Fecha: ${new Date().toLocaleDateString("es-AR")} | Tier: ${(cost?.tier as string) ?? "N/D"} | Fallos analizados: ${totalAnalyzed} | Costo: $${((cost?.total_cost_usd as number) ?? 0).toFixed(4)} USD</p>

<h2>Parte 1 — Cómo razonó cada agente</h2>
${agentSections}

<h2>Parte 2 — Cómo el sintetizador cruzó la información</h2>
<div class="synth">${synthNarrative}</div>

<div class="footer">Generado por LITIGIA — ${totalAnalyzed} agentes de IA analizaron jurisprudencia real argentina</div>
</body></html>`;

  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const w = window.open(url, "_blank");
  if (w) {
    w.onload = () => {
      w.print();
      URL.revokeObjectURL(url);
    };
  }
}

function buildAgentNarrative(fallo: FalloDetalle): string {
  const lines: string[] = [];
  const r = fallo.resultado;
  const label = r === "favorable" ? "FAVORABLE al actor" : r === "desfavorable" ? "DESFAVORABLE al actor" : r === "parcial" ? "PARCIALMENTE favorable" : "INADMISIBLE (no entró al fondo)";

  lines.push(`Analicé "${fallo.caratula}" (${fallo.tribunal}, ${fallo.fecha}).`);
  lines.push(`\nResultado: ${label}.`);

  if (fallo.via_procesal) lines.push(`Llegó al tribunal por: ${fallo.via_procesal}.`);
  if (fallo.hechos_determinantes) lines.push(`\nHechos decisivos: ${fallo.hechos_determinantes}`);
  if (fallo.doctrina_aplicada) lines.push(`\nDoctrina aplicada: ${fallo.doctrina_aplicada}.`);
  if (fallo.normas_citadas.length > 0) lines.push(`\nNormas invocadas: ${fallo.normas_citadas.join(", ")}.`);
  if (fallo.precedentes_citados.length > 0) lines.push(`Precedentes citados: ${fallo.precedentes_citados.join(", ")}.`);
  if (fallo.estrategia) lines.push(`\nEstrategia de la parte ganadora: ${fallo.estrategia}`);
  if (fallo.argumento_clave) lines.push(`Argumento que convenció al tribunal: ${fallo.argumento_clave}`);
  if (fallo.razon_resultado) lines.push(`\nPor qué se resolvió así: ${fallo.razon_resultado}`);
  if (fallo.prueba_decisiva && fallo.prueba_decisiva !== "N/D") lines.push(`Prueba decisiva: ${fallo.prueba_decisiva}`);
  if (fallo.quantum && fallo.quantum !== "N/D") lines.push(`Montos/costas: ${fallo.quantum}`);
  if (fallo.votos && fallo.votos !== "N/D" && fallo.votos !== "unánime") lines.push(`Votación: ${fallo.votos}`);
  if (fallo.relevancia_cliente) lines.push(`\nRelevancia para el caso del cliente: ${fallo.relevancia_cliente}`);

  return lines.join("\n");
}

function FalloCard({ fallo, index }: { fallo: FalloDetalle; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = RESULTADO_CONFIG[fallo.resultado] ?? RESULTADO_CONFIG.parcial;

  const fields: { label: string; value: string }[] = [
    { label: "Vía procesal", value: fallo.via_procesal },
    { label: "Doctrina aplicada", value: fallo.doctrina_aplicada },
    { label: "Hechos determinantes", value: fallo.hechos_determinantes },
    { label: "Prueba decisiva", value: fallo.prueba_decisiva },
    { label: "Estrategia", value: fallo.estrategia },
    { label: "Argumento clave", value: fallo.argumento_clave },
    { label: "Razón del resultado", value: fallo.razon_resultado },
    { label: "Relevancia para el cliente", value: fallo.relevancia_cliente },
    { label: "Quantum / Costas", value: fallo.quantum },
    { label: "Votos", value: fallo.votos },
  ].filter((f) => f.value && f.value !== "N/D");

  return (
    <div className="bg-[var(--container-high)] transition-all hover:bg-[var(--container-highest)]">
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left p-4 flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-bold px-2 py-0.5 uppercase tracking-wide" style={{ color: cfg.color, background: `color-mix(in srgb, ${cfg.color} 12%, transparent)` }}>
              {cfg.label}
            </span>
            <span className="text-[10px] text-[var(--muted)]">#{index + 1}</span>
          </div>
          <h5 className="font-heading font-bold text-sm text-[var(--primary)] leading-tight truncate">{fallo.caratula}</h5>
          <div className="flex items-center gap-2 mt-1 text-[10px] uppercase tracking-wide text-[var(--muted)]">
            {fallo.tribunal && <span>{fallo.tribunal}</span>}
            {fallo.tribunal && fallo.fecha && <span>|</span>}
            {fallo.fecha && <span>{fallo.fecha}</span>}
          </div>
        </div>
        <span className="text-xs text-[var(--primary)] font-heading">{expanded ? "−" : "+"}</span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-[var(--outline-variant)]/20 pt-3 animate-fade-in">
          {fallo.normas_citadas.length > 0 && (
            <div>
              <span className="text-[10px] font-semibold tracking-wide uppercase text-[var(--primary)]">Normas citadas</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {fallo.normas_citadas.map((n, i) => (
                  <span key={i} className="text-[10px] px-2 py-0.5 bg-[var(--container)] text-[var(--primary)]">{n}</span>
                ))}
              </div>
            </div>
          )}
          {fallo.precedentes_citados.length > 0 && (
            <div>
              <span className="text-[10px] font-semibold tracking-wide uppercase text-[var(--primary)]">Precedentes</span>
              <ul className="mt-1 text-xs space-y-0.5">
                {fallo.precedentes_citados.map((p, i) => (
                  <li key={i} className="text-[var(--muted)]">{p}</li>
                ))}
              </ul>
            </div>
          )}
          {fields.map((f, i) => (
            <div key={i} className="border-l-2 border-[var(--outline-variant)] pl-3">
              <span className="text-[10px] font-semibold tracking-wide uppercase text-[var(--primary)]">{f.label}</span>
              <p className="text-xs leading-relaxed mt-0.5 text-[var(--on-surface-variant)]">{f.value}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

type ResultadoFilter = "todos" | "favorable" | "desfavorable" | "parcial" | "inadmisible";

const FILTER_OPTIONS: { value: ResultadoFilter; label: string }[] = [
  { value: "todos", label: "Todos" },
  { value: "favorable", label: "Favorables" },
  { value: "desfavorable", label: "Desfavorables" },
  { value: "parcial", label: "Parciales" },
  { value: "inadmisible", label: "Inadmisibles" },
];

export function AnalisisResult({ data }: { data: Record<string, unknown> }) {
  const [falloFilter, setFalloFilter] = useState<ResultadoFilter>("todos");
  const [showFallos, setShowFallos] = useState(false);

  const cost = data.cost as { total_cost_usd?: number; input_tokens?: number; output_tokens?: number; calls?: number; tier?: string; reader_model?: string; synth_model?: string } | undefined;
  const pctFavorable = (data.porcentaje_favorable as number) ?? 0;
  const favorables = (data.favorables as number) ?? 0;
  const desfavorables = (data.desfavorables as number) ?? 0;
  const parciales = (data.parciales as number) ?? 0;
  const inadmisibles = (data.inadmisibles as number) ?? 0;
  const normas = (data.normas_clave as string[]) ?? [];
  const precedentes = (data.precedentes_para_citar as string[]) ?? [];
  const prueba = (data.prueba_necesaria as string[]) ?? [];
  const estrategiasOk = (data.estrategias_exitosas as Record<string, unknown>[]) ?? [];
  const estrategiasFail = (data.estrategias_fracasadas as Record<string, unknown>[]) ?? [];
  const recomendacion = (data.recomendacion_estrategica as string) ?? "";
  const patronFav = (data.patron_factico_favorable as string) ?? "";
  const patronDesfav = (data.patron_factico_desfavorable as string) ?? "";
  const rangoQuantum = (data.rango_quantum as string) ?? "";
  const patronCostas = (data.patron_costas as string) ?? "";
  const disidencias = (data.disidencias_relevantes as string[]) ?? [];
  const fallosDetalle = (data.fallos_analizados_detalle as FalloDetalle[]) ?? [];

  const filteredFallos = falloFilter === "todos"
    ? fallosDetalle
    : fallosDetalle.filter((f) => f.resultado === falloFilter);

  return (
    <div className="space-y-5 animate-slide-up">
      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-1">
        <StatBox value={`${pctFavorable.toFixed(0)}%`} label="Favorable" variant={pctFavorable >= 50 ? "gold" : "danger"} large />
        <StatBox value={favorables} label="Favorables" />
        <StatBox value={desfavorables} label="Desfavorables" variant="danger" />
        <StatBox value={parciales + inadmisibles} label="Parcial / Inadm." variant="muted" />
      </div>

      {/* Cost tracking */}
      {cost && cost.total_cost_usd !== undefined && (
        <div className="flex items-center justify-between px-4 py-3 bg-[var(--container-lowest)] text-[11px] tracking-wide">
          <div className="flex items-center gap-4 text-[var(--muted)]">
            <span className="uppercase">{cost.tier ?? "premium"}</span>
            <span>{cost.input_tokens?.toLocaleString()} in / {cost.output_tokens?.toLocaleString()} out</span>
            <span>{cost.calls} llamadas</span>
          </div>
          <span className="font-bold text-[var(--primary)]">
            USD ${cost.total_cost_usd.toFixed(4)}
          </span>
        </div>
      )}

      {/* PDF transparency download — only when reasoning data exists */}
      {fallosDetalle.length > 0 && fallosDetalle.some((f) => f.reasoning) && (
        <button
          onClick={() => generateTransparencyPDF(data, fallosDetalle)}
          className="w-full py-3 border border-[var(--primary-container)] text-[var(--primary)] font-semibold text-xs tracking-wide uppercase hover:bg-[var(--primary)]/10 transition-all"
        >
          Descargar informe de transparencia (PDF) — Cómo razonó cada agente
        </button>
      )}

      {/* Razonamiento del sintetizador — narrativa */}
      <Card>
        <CardHeader>Razonamiento del Sintetizador</CardHeader>
        <div className="text-sm leading-relaxed text-[var(--on-surface-variant)] space-y-3">
          <p>
            Analicé {(data.fallos_analizados as number) ?? 0} fallos.
            De los que entraron al fondo: {favorables} favorables, {desfavorables} desfavorables{parciales > 0 ? `, ${parciales} parciales` : ""}.
            {inadmisibles > 0 ? ` ${inadmisibles} fueron inadmisibles (rechazados sin entrar al fondo).` : ""}
            {" "}Porcentaje favorable (excluyendo inadmisibles): {pctFavorable.toFixed(0)}%.
          </p>
          {patronFav && (
            <p><strong className="text-[var(--primary)]">Patrón de los que ganaron:</strong> {patronFav}</p>
          )}
          {patronDesfav && (
            <p><strong className="text-[var(--danger)]">Patrón de los que perdieron:</strong> {patronDesfav}</p>
          )}
          {estrategiasOk.length > 0 && (
            <p>
              <strong className="text-[var(--primary)]">Estrategias exitosas encontradas:</strong> {estrategiasOk.length}.
              La más efectiva: &ldquo;{estrategiasOk[0]?.estrategia as string}&rdquo; ({(estrategiasOk[0]?.tasa_exito as number)?.toFixed(0)}% de éxito en {estrategiasOk[0]?.frecuencia as number} casos).
            </p>
          )}
          {normas.length > 0 && (
            <p><strong className="text-[var(--primary)]">Normas más citadas en favorables:</strong> {normas.slice(0, 5).join(", ")}.</p>
          )}
          {((data.riesgos as string[]) ?? []).length > 0 && (
            <p><strong className="text-[var(--danger)]">Riesgos identificados:</strong> {(data.riesgos as string[]).length} — cada uno basado en un caso concreto que perdió.</p>
          )}
        </div>
      </Card>

      {/* Recomendación estratégica */}
      {recomendacion && (
        <Card accent="gold">
          <CardHeader>Recomendación Estratégica</CardHeader>
          <p className="text-sm leading-relaxed text-[var(--on-surface)]">{recomendacion}</p>
        </Card>
      )}

      {/* Estrategias exitosas */}
      {estrategiasOk.length > 0 && (
        <Card>
          <CardHeader>Estrategias Exitosas</CardHeader>
          <div className="space-y-3">
            {estrategiasOk.map((e, i) => (
              <div key={i} className="border-l-2 border-[var(--primary)] pl-3">
                <div className="text-sm font-semibold text-[var(--on-surface)]">{e.estrategia as string}</div>
                <div className="text-[11px] text-[var(--muted)] mt-1">
                  {e.frecuencia as number} casos — {(e.tasa_exito as number)?.toFixed(0)}% éxito
                  {!!e.caso_ejemplo && <> — ej: <em className="text-[var(--on-surface-variant)]">{e.caso_ejemplo as string}</em></>}
                </div>
                {(e.leyes_asociadas as string[])?.length > 0 && (
                  <div className="text-[11px] text-[var(--primary)] mt-0.5">
                    {(e.leyes_asociadas as string[]).join(" · ")}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Normas + Precedentes */}
      <div className="grid grid-cols-2 gap-1">
        {normas.length > 0 && (
          <Card>
            <CardHeader>Normas Clave</CardHeader>
            <div className="flex flex-wrap gap-1.5">
              {normas.map((n, i) => (
                <span key={i} className="text-[11px] px-2 py-0.5 bg-[var(--container)] text-[var(--primary)]">{n}</span>
              ))}
            </div>
          </Card>
        )}
        {precedentes.length > 0 && (
          <Card>
            <CardHeader>Precedentes para Citar</CardHeader>
            <ul className="text-xs space-y-1">
              {precedentes.map((p, i) => (
                <li key={i} className="text-[var(--on-surface-variant)]">• {p}</li>
              ))}
            </ul>
          </Card>
        )}
      </div>

      {/* Prueba necesaria */}
      {prueba.length > 0 && (
        <Card accent="gold">
          <CardHeader>Prueba a Producir</CardHeader>
          <ul className="list-disc list-inside text-sm space-y-1 text-[var(--on-surface-variant)]">
            {prueba.map((p, i) => <li key={i}>{p}</li>)}
          </ul>
        </Card>
      )}

      {/* Contradicciones */}
      {((data.contradicciones as string[]) ?? []).length > 0 && (
        <Card accent="gold">
          <CardHeader>Contradicciones Jurisprudenciales</CardHeader>
          <ul className="list-disc list-inside text-sm space-y-2 text-[var(--on-surface-variant)]">
            {(data.contradicciones as string[]).map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </Card>
      )}

      {/* Quantum + Costas + Disidencias */}
      {(rangoQuantum || patronCostas || disidencias.length > 0) && (
        <div className="grid grid-cols-2 gap-1">
          {(rangoQuantum && rangoQuantum !== "N/D") && (
            <Card>
              <CardHeader>Estimación de Montos</CardHeader>
              <p className="text-sm leading-relaxed text-[var(--on-surface-variant)]">{rangoQuantum}</p>
            </Card>
          )}
          {(patronCostas && patronCostas !== "N/D") && (
            <Card>
              <CardHeader>Patrón de Costas</CardHeader>
              <p className="text-sm leading-relaxed text-[var(--on-surface-variant)]">{patronCostas}</p>
            </Card>
          )}
        </div>
      )}

      {disidencias.length > 0 && (
        <Card>
          <CardHeader>Disidencias Relevantes</CardHeader>
          <ul className="list-disc list-inside text-sm space-y-1 text-[var(--on-surface-variant)]">
            {disidencias.map((d, i) => <li key={i}>{d}</li>)}
          </ul>
        </Card>
      )}

      {/* Riesgos */}
      {((data.riesgos as string[]) ?? []).length > 0 && (
        <Card accent="danger">
          <CardHeader variant="danger">Riesgos Identificados</CardHeader>
          <ul className="list-disc list-inside text-sm space-y-1 text-[var(--on-surface-variant)]">
            {(data.riesgos as string[]).map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </Card>
      )}

      {/* Estrategias fracasadas */}
      {estrategiasFail.length > 0 && (
        <Card>
          <CardHeader variant="danger">Estrategias que No Funcionaron</CardHeader>
          <div className="space-y-2">
            {estrategiasFail.map((e, i) => (
              <div key={i} className="border-l-2 border-[var(--danger)] pl-3">
                <div className="text-sm text-[var(--on-surface)]">{e.estrategia as string}</div>
                <div className="text-[11px] text-[var(--muted)] mt-0.5">
                  {e.frecuencia as number} intentos — {(e.tasa_exito as number)?.toFixed(0)}% éxito
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Fallos analizados — detail */}
      {fallosDetalle.length > 0 && (
        <div className="bg-[var(--container)] p-5">
          <button onClick={() => setShowFallos(!showFallos)} className="w-full flex items-center justify-between">
            <h4 className="text-[11px] font-semibold tracking-[0.15em] uppercase text-[var(--primary)]">
              Fallos Analizados ({fallosDetalle.length})
            </h4>
            <span className="text-xs text-[var(--primary)] font-heading">
              {showFallos ? "Ocultar" : "Ver todos"}
            </span>
          </button>

          {showFallos && (
            <div className="mt-4 space-y-1 animate-fade-in">
              <div className="flex flex-wrap gap-2 mb-3">
                {FILTER_OPTIONS.map((opt) => {
                  const isActive = falloFilter === opt.value;
                  const count = opt.value === "todos"
                    ? fallosDetalle.length
                    : fallosDetalle.filter((f) => f.resultado === opt.value).length;
                  if (count === 0 && opt.value !== "todos") return null;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => setFalloFilter(opt.value)}
                      className="text-[11px] px-3 py-1 tracking-wide uppercase transition-all"
                      style={{
                        background: isActive ? "var(--primary)" : "var(--container-high)",
                        color: isActive ? "var(--on-primary)" : "var(--primary)",
                      }}
                    >
                      {opt.label} ({count})
                    </button>
                  );
                })}
              </div>
              <div className="space-y-1 max-h-[600px] overflow-y-auto custom-scrollbar pr-1">
                {filteredFallos.map((fallo, i) => (
                  <FalloCard key={i} fallo={fallo} index={i} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
