"use client";

import { useState } from "react";
import { downloadDocx } from "@/lib/api";

export function JurisprudenciaResult({ data }: { data: Record<string, unknown> }) {
  const fallos = (data.fallos ?? []) as Array<{
    tribunal: string;
    fecha: string;
    caratula: string;
    resumen: string;
    argumento_clave: string;
    cita_textual: string;
    score: number;
    texto_completo: string;
    materia: string;
    fuente: string;
  }>;

  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center justify-between text-sm text-[var(--color-text-muted)] pb-3 border-b border-[var(--color-border)]">
        <span>
          {(data.total_encontrados as number) ?? 0} fallos encontrados
        </span>
      </div>

      {fallos.map((fallo, i) => (
        <div
          key={i}
          className="border border-[var(--color-border)] rounded-lg p-4 hover:shadow-md transition-shadow bg-[var(--color-surface)]"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h4 className="font-bold text-[var(--color-accent)] text-sm leading-tight">
                {fallo.caratula || "Sin caratula"}
              </h4>
              <div className="flex items-center gap-2 mt-1 text-xs text-[var(--color-text-muted)]">
                {fallo.tribunal && <span>{fallo.tribunal}</span>}
                {fallo.tribunal && fallo.fecha && <span>|</span>}
                {fallo.fecha && <span>{fallo.fecha}</span>}
                {fallo.materia && <><span>|</span><span className="uppercase">{fallo.materia}</span></>}
              </div>
            </div>
            <div className="px-2 py-1 rounded-full bg-[var(--color-info-bg)] text-[var(--color-accent)] text-xs font-bold whitespace-nowrap">
              {(fallo.score * 100).toFixed(0)}%
            </div>
          </div>

          {fallo.resumen && (
            <p className="mt-3 text-sm text-[var(--color-text)]">{fallo.resumen}</p>
          )}

          {fallo.argumento_clave && fallo.argumento_clave !== fallo.caratula && (
            <div className="mt-2 p-2 rounded bg-[var(--color-surface-alt)]">
              <span className="text-xs font-bold text-[var(--color-accent)]">
                Argumento clave:
              </span>
              <p className="text-sm mt-0.5">{fallo.argumento_clave}</p>
            </div>
          )}

          {fallo.cita_textual && (
            <blockquote className="mt-2 text-sm italic border-l-3 border-[var(--color-accent)] pl-3 text-[var(--color-text-muted)]">
              &ldquo;{fallo.cita_textual}&rdquo;
            </blockquote>
          )}

          <div className="mt-3 flex items-center gap-3">
            {fallo.texto_completo && (
              <button
                onClick={() => setExpanded(expanded === i ? null : i)}
                className="text-xs font-semibold text-[var(--color-accent)] hover:text-[var(--color-primary-light)] transition-colors"
              >
                {expanded === i ? "Ocultar texto completo" : "Ver texto completo"}
              </button>
            )}
          </div>
          {expanded === i && fallo.texto_completo && (
            <div className="mt-2 p-4 bg-[var(--color-surface-alt)] border border-[var(--color-border)] rounded-lg max-h-[500px] overflow-y-auto custom-scrollbar">
              <pre className="whitespace-pre-wrap font-serif text-xs leading-relaxed">
                {fallo.texto_completo}
              </pre>
            </div>
          )}
        </div>
      ))}

      {fallos.length === 0 && (
        <div className="text-center py-8 text-[var(--color-text-muted)]">
          No se encontraron fallos relevantes para este caso.
        </div>
      )}
    </div>
  );
}

export function EscritoResult({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="space-y-4 animate-slide-up">
      <div className="bg-[var(--color-surface-alt)] border border-[var(--color-border)] rounded-lg p-5 max-h-[600px] overflow-y-auto custom-scrollbar">
        <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed">
          {data.contenido_texto as string}
        </pre>
      </div>

      <div className="flex items-center gap-3">
        {data.archivo_docx_base64 && (
          <button
            onClick={() =>
              downloadDocx(data.archivo_docx_base64 as string, "escrito_litigia.docx")
            }
            className="px-6 py-2.5 bg-transparent border border-[var(--color-accent)] text-[var(--color-accent)] rounded-lg font-semibold hover:bg-[var(--color-accent-muted)] transition-all duration-300"
          >
            Descargar .docx
          </button>
        )}
        {((data.jurisprudencia_citada as unknown[]) ?? []).length > 0 && (
          <span className="text-xs text-[var(--color-text-muted)]">
            {(data.jurisprudencia_citada as unknown[]).length} fallos citados
          </span>
        )}
      </div>
    </div>
  );
}

export function ResumenResult({ data }: { data: Record<string, unknown> }) {
  const sections = [
    { key: "hechos", label: "Hechos" },
    { key: "cuestion_juridica", label: "Cuestion Juridica" },
    { key: "argumentos_actor", label: "Argumentos del Actor" },
    { key: "argumentos_demandado", label: "Argumentos del Demandado" },
    { key: "resolucion", label: "Resolucion" },
    { key: "doctrina_aplicada", label: "Doctrina Aplicada" },
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      {sections.map(({ key, label }) => (
        <div
          key={key}
          className="border-l-3 border-[var(--color-primary)] pl-4 py-1"
        >
          <h4 className="font-bold text-sm text-[var(--color-accent)] uppercase tracking-wide">
            {label}
          </h4>
          <p className="text-sm mt-1 leading-relaxed">{data[key] as string}</p>
        </div>
      ))}

      {(data.articulos_citados as string[])?.length > 0 && (
        <div className="bg-[var(--color-surface-alt)] rounded-lg p-4">
          <h4 className="font-bold text-sm text-[var(--color-accent)] mb-2">
            Articulos Citados
          </h4>
          <div className="flex flex-wrap gap-2">
            {(data.articulos_citados as string[]).map((art, i) => (
              <span
                key={i}
                className="px-2 py-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded text-xs"
              >
                {art}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function OficioResult({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="animate-slide-up">
      <div className="bg-[var(--color-surface-alt)] border border-[var(--color-border)] rounded-lg p-5">
        <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed">
          {(data as { contenido?: string }).contenido}
        </pre>
      </div>
    </div>
  );
}

// ── Fallo detail types ──────────────────────────────────────────

interface FalloDetalle {
  caratula: string;
  tribunal: string;
  fecha: string;
  resultado: string;
  normas_citadas: string[];
  precedentes_citados: string[];
  via_procesal: string;
  doctrina_aplicada: string;
  hechos_determinantes: string;
  prueba_decisiva: string;
  quantum: string;
  votos: string;
  estrategia: string;
  argumento_clave: string;
  razon_resultado: string;
  relevancia_cliente: string;
  score: number;
  source_id: string;
}

const RESULTADO_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  favorable: { label: "Favorable", color: "var(--color-accent)", bg: "var(--color-accent-muted)" },
  desfavorable: { label: "Desfavorable", color: "var(--color-danger)", bg: "var(--color-danger-bg)" },
  parcial: { label: "Parcial", color: "var(--color-text-muted)", bg: "rgba(107,104,120,0.08)" },
  inadmisible: { label: "Inadmisible", color: "var(--color-text-muted)", bg: "rgba(107,104,120,0.08)" },
};

function FalloCard({ fallo, index }: { fallo: FalloDetalle; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = RESULTADO_CONFIG[fallo.resultado] ?? RESULTADO_CONFIG.parcial;

  const fields: { label: string; value: string }[] = [
    { label: "Via procesal", value: fallo.via_procesal },
    { label: "Doctrina aplicada", value: fallo.doctrina_aplicada },
    { label: "Hechos determinantes", value: fallo.hechos_determinantes },
    { label: "Prueba decisiva", value: fallo.prueba_decisiva },
    { label: "Estrategia", value: fallo.estrategia },
    { label: "Argumento clave", value: fallo.argumento_clave },
    { label: "Razon del resultado", value: fallo.razon_resultado },
    { label: "Relevancia para el cliente", value: fallo.relevancia_cliente },
    { label: "Quantum / Costas", value: fallo.quantum },
    { label: "Votos", value: fallo.votos },
  ].filter((f) => f.value && f.value !== "N/D");

  return (
    <div className="border border-[var(--color-border)] rounded-lg bg-[var(--color-surface)] transition-all hover:shadow-md">
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 flex items-start justify-between gap-3"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
              style={{ background: cfg.bg, color: cfg.color }}
            >
              {cfg.label}
            </span>
            <span className="text-[10px] text-[var(--color-text-muted)]">
              #{index + 1}
            </span>
          </div>
          <h5 className="font-bold text-sm text-[var(--color-accent)] leading-tight truncate">
            {fallo.caratula}
          </h5>
          <div className="flex items-center gap-2 mt-1 text-xs text-[var(--color-text-muted)]">
            {fallo.tribunal && <span>{fallo.tribunal}</span>}
            {fallo.tribunal && fallo.fecha && <span>|</span>}
            {fallo.fecha && <span>{fallo.fecha}</span>}
          </div>
        </div>
        <span
          className="text-xs text-[var(--color-accent)] shrink-0 mt-1"
          style={{ fontFamily: "Georgia, serif" }}
        >
          {expanded ? "−" : "+"}
        </span>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-[var(--color-border)] pt-3 animate-fade-in">
          {/* Normas + Precedentes tags */}
          {fallo.normas_citadas.length > 0 && (
            <div>
              <span className="text-[10px] font-bold text-[var(--color-accent)] uppercase tracking-wide">
                Normas citadas
              </span>
              <div className="flex flex-wrap gap-1 mt-1">
                {fallo.normas_citadas.map((n, i) => (
                  <span
                    key={i}
                    className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-accent-muted)] text-[var(--color-accent)]"
                  >
                    {n}
                  </span>
                ))}
              </div>
            </div>
          )}

          {fallo.precedentes_citados.length > 0 && (
            <div>
              <span className="text-[10px] font-bold text-[var(--color-accent)] uppercase tracking-wide">
                Precedentes citados
              </span>
              <ul className="mt-1 text-xs space-y-0.5">
                {fallo.precedentes_citados.map((p, i) => (
                  <li key={i} className="text-[var(--color-text-muted)]">• {p}</li>
                ))}
              </ul>
            </div>
          )}

          {/* All extracted fields */}
          {fields.map((f, i) => (
            <div key={i} className="border-l-2 border-[var(--color-border-active)] pl-3">
              <span className="text-[10px] font-bold text-[var(--color-accent)] uppercase tracking-wide">
                {f.label}
              </span>
              <p className="text-xs leading-relaxed mt-0.5">{f.value}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Filter pills ────────────────────────────────────────────────

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

  const pctColor = pctFavorable >= 60
    ? "text-[var(--color-accent)]"
    : pctFavorable >= 40
    ? "text-[var(--color-accent)]"
    : "text-[var(--color-danger)]";

  const pctBg = pctFavorable >= 60
    ? "bg-[var(--color-accent-muted)]"
    : pctFavorable >= 40
    ? "bg-[var(--color-accent-muted)]"
    : "bg-[var(--color-danger-bg)]";

  return (
    <div className="space-y-5 animate-slide-up">
      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-3">
        <div className={`${pctBg} p-4 rounded-xl text-center`}>
          <div className={`text-3xl font-bold ${pctColor}`}>{pctFavorable.toFixed(0)}%</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">Favorable</div>
        </div>
        <div className="bg-[var(--color-info-bg)] p-4 rounded-xl text-center">
          <div className="text-lg font-bold text-[var(--color-accent)]">{favorables}</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">Favorables</div>
        </div>
        <div className="bg-[var(--color-info-bg)] p-4 rounded-xl text-center">
          <div className="text-lg font-bold text-[var(--color-danger)]">{desfavorables}</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">Desfavorables</div>
        </div>
        <div className="bg-[var(--color-info-bg)] p-4 rounded-xl text-center">
          <div className="text-lg font-bold text-[var(--color-text-muted)]">{parciales + inadmisibles}</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-1">Parcial / Inadm.</div>
        </div>
      </div>

      {/* Recomendacion estrategica */}
      {recomendacion && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border-active)] rounded-lg p-4">
          <h4 className="font-bold text-sm gold-text mb-2">Recomendacion estrategica</h4>
          <p className="text-sm leading-relaxed">{recomendacion}</p>
        </div>
      )}

      {/* Estrategias exitosas */}
      {estrategiasOk.length > 0 && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4">
          <h4 className="font-bold text-sm text-[var(--color-accent)] mb-2">Estrategias exitosas</h4>
          <div className="space-y-3">
            {estrategiasOk.map((e, i) => (
              <div key={i} className="border-l-2 border-[var(--color-accent)] pl-3">
                <div className="text-sm font-semibold">{e.estrategia as string}</div>
                <div className="text-xs text-[var(--color-text-muted)] mt-1">
                  {e.frecuencia as number} casos — {(e.tasa_exito as number)?.toFixed(0)}% exito
                  {e.caso_ejemplo && <> — ej: <em>{e.caso_ejemplo as string}</em></>}
                </div>
                {(e.leyes_asociadas as string[])?.length > 0 && (
                  <div className="text-xs text-[var(--color-accent)] mt-0.5">
                    {(e.leyes_asociadas as string[]).join(" · ")}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Normas clave + Precedentes */}
      <div className="grid grid-cols-2 gap-4">
        {normas.length > 0 && (
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4">
            <h4 className="font-bold text-sm text-[var(--color-accent)] mb-2">Normas clave</h4>
            <div className="flex flex-wrap gap-1.5">
              {normas.map((n, i) => (
                <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-accent-muted)] text-[var(--color-accent)]">
                  {n}
                </span>
              ))}
            </div>
          </div>
        )}
        {precedentes.length > 0 && (
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4">
            <h4 className="font-bold text-sm text-[var(--color-accent)] mb-2">Precedentes para citar</h4>
            <ul className="text-xs space-y-1">
              {precedentes.map((p, i) => (
                <li key={i} className="text-[var(--color-text)]">• {p}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Prueba necesaria */}
      {prueba.length > 0 && (
        <div className="bg-[var(--color-info-bg)] border border-[var(--color-border)] rounded-lg p-4">
          <h4 className="font-bold text-sm text-[var(--color-accent)] mb-2">Prueba a producir</h4>
          <ul className="list-disc list-inside text-sm space-y-1">
            {prueba.map((p, i) => <li key={i}>{p}</li>)}
          </ul>
        </div>
      )}

      {/* Riesgos */}
      {((data.riesgos as string[]) ?? []).length > 0 && (
        <div className="bg-[var(--color-danger-bg)] border border-[var(--color-border)] rounded-lg p-4">
          <h4 className="font-bold text-sm text-[var(--color-danger)] mb-2">Riesgos identificados</h4>
          <ul className="list-disc list-inside text-sm space-y-1">
            {(data.riesgos as string[]).map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Estrategias fracasadas */}
      {estrategiasFail.length > 0 && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4">
          <h4 className="font-bold text-sm text-[var(--color-danger)] mb-2">Estrategias que no funcionaron</h4>
          <div className="space-y-2">
            {estrategiasFail.map((e, i) => (
              <div key={i} className="border-l-2 border-[var(--color-danger)] pl-3">
                <div className="text-sm">{e.estrategia as string}</div>
                <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  {e.frecuencia as number} intentos — {(e.tasa_exito as number)?.toFixed(0)}% exito
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Fallos analizados — full detail ────────────────────── */}
      {fallosDetalle.length > 0 && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border-active)] rounded-lg p-4">
          <button
            onClick={() => setShowFallos(!showFallos)}
            className="w-full flex items-center justify-between"
          >
            <h4 className="font-bold text-sm gold-text">
              Fallos analizados ({fallosDetalle.length})
            </h4>
            <span className="text-xs text-[var(--color-accent)]" style={{ fontFamily: "Georgia, serif" }}>
              {showFallos ? "Ocultar" : "Ver todos"}
            </span>
          </button>

          {showFallos && (
            <div className="mt-4 space-y-3 animate-fade-in">
              {/* Filter pills */}
              <div className="flex flex-wrap gap-2">
                {FILTER_OPTIONS.map((opt) => {
                  const isActive = falloFilter === opt.value;
                  const count =
                    opt.value === "todos"
                      ? fallosDetalle.length
                      : fallosDetalle.filter((f) => f.resultado === opt.value).length;
                  if (count === 0 && opt.value !== "todos") return null;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => setFalloFilter(opt.value)}
                      className="text-xs px-3 py-1 rounded-full transition-all"
                      style={{
                        background: isActive ? "var(--color-accent)" : "var(--color-accent-muted)",
                        color: isActive ? "#fff" : "var(--color-accent)",
                        fontFamily: "Georgia, serif",
                      }}
                    >
                      {opt.label} ({count})
                    </button>
                  );
                })}
              </div>

              {/* Fallo cards */}
              <div className="space-y-2 max-h-[600px] overflow-y-auto custom-scrollbar pr-1">
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
