"use client";

export type Tool = "jurisprudencia" | "escrito" | "resumen" | "oficio" | "analisis";

const TOOLS: { id: Tool; label: string; desc: string }[] = [
  { id: "jurisprudencia", label: "Jurisprudencia", desc: "Buscar fallos relevantes" },
  { id: "escrito", label: "Escrito", desc: "Generar escritos judiciales" },
  { id: "resumen", label: "Resumen", desc: "Resumir un fallo" },
  { id: "oficio", label: "Oficio", desc: "Oficios a terceros" },
  { id: "analisis", label: "Analisis", desc: "Evaluar chances" },
];

export function ToolSelector({
  active,
  onChange,
}: {
  active: Tool;
  onChange: (tool: Tool) => void;
}) {
  return (
    <div className="grid grid-cols-5 gap-3">
      {TOOLS.map((tool) => {
        const isActive = active === tool.id;
        return (
          <button
            key={tool.id}
            onClick={() => onChange(tool.id)}
            style={{
              transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
              transform: isActive ? "translateY(-2px)" : "translateY(0)",
            }}
            className={`group relative px-3 py-4 rounded-2xl border text-center backdrop-blur-xl cursor-pointer ${
              isActive
                ? "border-[var(--color-border-active)] bg-[var(--color-surface-active)] shadow-xl shadow-amber-800/8"
                : "border-[var(--color-border)] bg-[var(--color-surface)] shadow-md shadow-black/4 hover:shadow-lg hover:shadow-amber-800/6 hover:border-[var(--color-border-active)] hover:bg-[var(--color-surface-hover)]"
            }`}
          >
            <div className={`font-semibold text-sm transition-all duration-300 ${
              isActive ? "gold-text" : "text-[var(--color-text)]"
            }`}>
              {tool.label}
            </div>
            <div className={`text-[11px] mt-1 transition-all duration-300 ${
              isActive ? "text-[var(--color-accent)]" : "text-[var(--color-text-muted)]"
            }`}>
              {tool.desc}
            </div>
            {isActive && (
              <div
                className="absolute bottom-0 left-1/2 -translate-x-1/2 h-[2px] bg-[var(--color-accent)] rounded-full animate-fade-in"
                style={{ width: "40%" }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
