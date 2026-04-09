"use client";

import { useState } from "react";
import { downloadDocx } from "@/lib/api";
import { Card, CardHeader, StatBox, Chip } from "@/components/ui";

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
}

const RESULTADO_CONFIG: Record<string, { label: string; color: string }> = {
  favorable: { label: "Favorable", color: "var(--primary)" },
  desfavorable: { label: "Desfavorable", color: "var(--danger)" },
  parcial: { label: "Parcial", color: "var(--muted)" },
  inadmisible: { label: "Inadmisible", color: "var(--muted)" },
};

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
                  <li key={i} className="text-[var(--muted)]">• {p}</li>
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
