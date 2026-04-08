"use client";

export type Tool = "jurisprudencia" | "escrito" | "resumen" | "oficio" | "analisis";

const TOOLS: { id: Tool; label: string; desc: string; icon: string }[] = [
  {
    id: "jurisprudencia",
    label: "Jurisprudencia",
    desc: "Buscar fallos relevantes",
    icon: "Lupa",
  },
  {
    id: "escrito",
    label: "Escrito",
    desc: "Generar escritos judiciales",
    icon: "Doc",
  },
  {
    id: "resumen",
    label: "Resumen",
    desc: "Resumir un fallo",
    icon: "Sum",
  },
  {
    id: "oficio",
    label: "Oficio",
    desc: "Oficios a terceros",
    icon: "Ofi",
  },
  {
    id: "analisis",
    label: "Analisis",
    desc: "Evaluar chances",
    icon: "Est",
  },
];

export function ToolSelector({
  active,
  onChange,
}: {
  active: Tool;
  onChange: (tool: Tool) => void;
}) {
  return (
    <div className="grid grid-cols-5 gap-2">
      {TOOLS.map((tool) => {
        const isActive = active === tool.id;
        return (
          <button
            key={tool.id}
            onClick={() => onChange(tool.id)}
            className={`group relative px-3 py-4 rounded-xl border-2 transition-all duration-200 text-center ${
              isActive
                ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-white shadow-md"
                : "border-[var(--color-border)] bg-white hover:border-[var(--color-primary-light)] hover:shadow-sm"
            }`}
          >
            <div
              className={`text-xs font-bold mb-1 ${
                isActive ? "text-[var(--color-accent)]" : "text-[var(--color-primary)]"
              }`}
            >
              {tool.icon}
            </div>
            <div className="font-semibold text-sm">{tool.label}</div>
            <div
              className={`text-[11px] mt-0.5 ${
                isActive ? "text-gray-300" : "text-[var(--color-text-muted)]"
              }`}
            >
              {tool.desc}
            </div>
          </button>
        );
      })}
    </div>
  );
}
