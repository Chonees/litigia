"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { getSavedItems, deleteSavedItem, type SavedItem, type SavedItemType } from "@/lib/saved-items";
import { SectionHeader } from "@/components/ui";
import {
  JurisprudenciaResult,
  EscritoResult,
  ResumenResult,
  OficioResult,
  AnalisisResult,
} from "@/components/results";

const TYPE_LABELS: Record<SavedItemType, string> = {
  jurisprudencia: "Jurisprudencia",
  escrito: "Escrito Judicial",
  resumen: "Resumen de Fallo",
  oficio: "Oficio Judicial",
  analisis: "Análisis Predictivo",
};

const FILTER_OPTIONS: { value: SavedItemType | "todos"; label: string }[] = [
  { value: "todos", label: "Todos" },
  { value: "jurisprudencia", label: "Jurisprudencia" },
  { value: "escrito", label: "Escritos" },
  { value: "resumen", label: "Resúmenes" },
  { value: "oficio", label: "Oficios" },
  { value: "analisis", label: "Análisis" },
];

function ResultRenderer({ item }: { item: SavedItem }) {
  const output = item.data.output as Record<string, unknown>;

  switch (item.type) {
    case "jurisprudencia":
      return <JurisprudenciaResult data={output} />;
    case "escrito":
      return <EscritoResult data={output} />;
    case "resumen":
      return <ResumenResult data={output} />;
    case "oficio":
      return <OficioResult data={output} />;
    case "analisis":
      return <AnalisisResult data={output} />;
  }
}

export default function GuardadosPage() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<SavedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<SavedItemType | "todos">("todos");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !user) { setLoading(false); return; }

    setLoading(true);
    getSavedItems(filter === "todos" ? undefined : filter)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [user, authLoading, filter]);

  async function handleDelete(id: string) {
    setDeleting(id);
    try {
      await deleteSavedItem(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch { /* ignore */ }
    setDeleting(null);
  }

  return (
    <div className="page-enter space-y-8">
      <SectionHeader label="Personal Archive" title="Mis Guardados" />

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {FILTER_OPTIONS.map((opt) => {
          const isActive = filter === opt.value;
          return (
            <button
              key={opt.value}
              onClick={() => setFilter(opt.value)}
              className="text-[11px] px-4 py-2 tracking-wide uppercase font-medium transition-all duration-300"
              style={{
                background: isActive ? "var(--primary)" : "var(--surface)",
                color: isActive ? "var(--on-primary)" : "var(--muted)",
                border: `1px solid ${isActive ? "var(--primary)" : "var(--outline-variant)"}`,
              }}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {/* Items */}
      {loading ? (
        <div className="text-center py-12 animate-pulse-slow text-[var(--muted)]">Cargando...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 animate-fade-in">
          <p className="text-sm text-[var(--muted)]">No tenés items guardados todavía.</p>
        </div>
      ) : (
        <div className="space-y-4 stagger-children">
          {items.map((item) => {
            const isExpanded = expanded === item.id;
            const input = item.data.input as Record<string, unknown> | null;

            return (
              <div key={item.id} className="bg-[var(--surface)] border border-[var(--outline-variant)] transition-all duration-300 hover:border-[var(--primary)]/30">
                {/* Header — always visible */}
                <div className="p-5 flex items-start justify-between gap-4">
                  <button
                    onClick={() => setExpanded(isExpanded ? null : item.id)}
                    className="flex-1 text-left min-w-0"
                  >
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-[10px] px-2 py-0.5 tracking-wide uppercase font-medium bg-[var(--container-lowest)] text-[var(--primary)]">
                        {TYPE_LABELS[item.type]}
                      </span>
                      <span className="text-[10px] text-[var(--muted)]">
                        {new Date(item.created_at).toLocaleDateString("es-AR", {
                          day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
                        })}
                      </span>
                    </div>
                    <h3 className="font-heading font-bold text-sm text-[var(--on-surface)] truncate">
                      {item.title}
                    </h3>
                    {input && typeof input === "object" && "descripcion_caso" in input && (
                      <p className="mt-1 text-xs text-[var(--muted)] line-clamp-2">
                        {String(input.descripcion_caso)}
                      </p>
                    )}
                  </button>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => setExpanded(isExpanded ? null : item.id)}
                      className="text-[11px] text-[var(--primary)] hover:underline"
                    >
                      {isExpanded ? "Cerrar" : "Ver completo"}
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      disabled={deleting === item.id}
                      className="text-[var(--muted)] hover:text-[var(--danger)] transition-colors p-1"
                    >
                      {deleting === item.id ? (
                        <span className="text-xs animate-pulse-slow">...</span>
                      ) : (
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                {/* Expanded — full result rendered with original components */}
                {isExpanded && (
                  <div className="border-t border-[var(--outline-variant)]/50 p-5 animate-slide-up">
                    <ResultRenderer item={item} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
