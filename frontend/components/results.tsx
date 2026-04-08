"use client";

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
  }>;

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center justify-between text-sm text-[var(--color-text-muted)] pb-3 border-b border-[var(--color-border)]">
        <span>
          {(data.total_encontrados as number) ?? 0} fallos encontrados
        </span>
        <span className="text-xs">
          Terminos: {((data.query_expandida as string[]) ?? []).join(" | ")}
        </span>
      </div>

      {fallos.map((fallo, i) => (
        <div
          key={i}
          className="border border-[var(--color-border)] rounded-lg p-4 hover:shadow-md transition-shadow bg-white"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h4 className="font-bold text-[var(--color-primary)] text-sm leading-tight">
                {fallo.caratula || "Sin caratula"}
              </h4>
              <div className="flex items-center gap-2 mt-1 text-xs text-[var(--color-text-muted)]">
                <span>{fallo.tribunal}</span>
                <span>|</span>
                <span>{fallo.fecha}</span>
              </div>
            </div>
            <div className="px-2 py-1 rounded-full bg-[var(--color-info-bg)] text-[var(--color-primary)] text-xs font-bold whitespace-nowrap">
              {(fallo.score * 100).toFixed(0)}%
            </div>
          </div>

          <p className="mt-3 text-sm text-gray-700">{fallo.resumen}</p>

          <div className="mt-2 p-2 rounded bg-[var(--color-surface-alt)]">
            <span className="text-xs font-bold text-[var(--color-primary)]">
              Argumento clave:
            </span>
            <p className="text-sm mt-0.5">{fallo.argumento_clave}</p>
          </div>

          {fallo.cita_textual && (
            <blockquote className="mt-2 text-sm italic border-l-3 border-[var(--color-accent)] pl-3 text-gray-500">
              &ldquo;{fallo.cita_textual}&rdquo;
            </blockquote>
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
            className="px-6 py-2.5 bg-[var(--color-accent)] text-white rounded-lg font-semibold hover:bg-[var(--color-accent-hover)] transition-colors shadow-sm"
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
          <h4 className="font-bold text-sm text-[var(--color-primary)] uppercase tracking-wide">
            {label}
          </h4>
          <p className="text-sm mt-1 leading-relaxed">{data[key] as string}</p>
        </div>
      ))}

      {(data.articulos_citados as string[])?.length > 0 && (
        <div className="bg-[var(--color-surface-alt)] rounded-lg p-4">
          <h4 className="font-bold text-sm text-[var(--color-primary)] mb-2">
            Articulos Citados
          </h4>
          <div className="flex flex-wrap gap-2">
            {(data.articulos_citados as string[]).map((art, i) => (
              <span
                key={i}
                className="px-2 py-1 bg-white border border-[var(--color-border)] rounded text-xs"
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

export function AnalisisResult({ data }: { data: Record<string, unknown> }) {
  const pctFavorable = (data.porcentaje_favorable as number) ?? 0;

  return (
    <div className="space-y-5 animate-slide-up">
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[var(--color-info-bg)] p-5 rounded-xl text-center">
          <div className="text-4xl font-bold text-[var(--color-primary)]">
            {data.fallos_analizados as number}
          </div>
          <div className="text-sm text-[var(--color-text-muted)] mt-1">
            Fallos analizados
          </div>
        </div>
        <div
          className={`p-5 rounded-xl text-center ${
            pctFavorable >= 60
              ? "bg-[var(--color-success-bg)]"
              : pctFavorable >= 40
              ? "bg-yellow-50"
              : "bg-[var(--color-danger-bg)]"
          }`}
        >
          <div
            className={`text-4xl font-bold ${
              pctFavorable >= 60
                ? "text-[var(--color-success)]"
                : pctFavorable >= 40
                ? "text-yellow-600"
                : "text-[var(--color-danger)]"
            }`}
          >
            {pctFavorable.toFixed(0)}%
          </div>
          <div className="text-sm text-[var(--color-text-muted)] mt-1">
            Favorable
          </div>
        </div>
      </div>

      <div className="bg-white border border-[var(--color-border)] rounded-lg p-4">
        <h4 className="font-bold text-sm text-[var(--color-primary)]">
          Argumento mas fuerte
        </h4>
        <p className="text-sm mt-1">{data.argumento_mas_fuerte as string}</p>
      </div>

      {((data.riesgos as string[]) ?? []).length > 0 && (
        <div className="bg-[var(--color-danger-bg)] border border-red-200 rounded-lg p-4">
          <h4 className="font-bold text-sm text-[var(--color-danger)]">
            Riesgos identificados
          </h4>
          <ul className="list-disc list-inside text-sm mt-1 space-y-1">
            {(data.riesgos as string[]).map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
