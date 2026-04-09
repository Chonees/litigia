import Link from "next/link";

const TOOLS = [
  {
    href: "/jurisprudencia",
    icon: "⚖",
    title: "Jurisprudencia",
    desc: "Búsqueda inteligente en +400.000 fallos. Encontrá precedentes relevantes para tu caso con análisis semántico.",
    label: "Archive Search",
  },
  {
    href: "/escrito",
    icon: "✎",
    title: "Escrito Judicial",
    desc: "Generá escritos judiciales completos con citas a jurisprudencia real y formato institucional.",
    label: "Drafting Engine",
  },
  {
    href: "/resumen",
    icon: "▤",
    title: "Resumir Fallo",
    desc: "Resumen estructurado de fallos: hechos, cuestión jurídica, fundamentos y decisión.",
    label: "Case Summarizer",
  },
  {
    href: "/oficio",
    icon: "✉",
    title: "Oficio Judicial",
    desc: "Oficios formales a organismos públicos y privados con datos del expediente.",
    label: "Official Communication",
  },
  {
    href: "/analisis",
    icon: "◈",
    title: "Análisis Predictivo",
    desc: "100 agentes IA analizan jurisprudencia y generan un informe estratégico con tasa de éxito.",
    label: "Visual Intelligence",
  },
];

export default function Home() {
  return (
    <div className="page-enter space-y-20">
      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="text-center pt-16 pb-4 animate-fade-in">
        <h1 className="font-heading text-5xl md:text-6xl font-bold text-[var(--on-surface)] tracking-tight leading-tight">
          Inteligencia Legal<br />
          <span className="gold-text">de Grado Institucional</span>
        </h1>
        <p className="mt-5 text-sm tracking-[0.2em] uppercase text-[var(--muted)] animate-fade-in" style={{ animationDelay: "0.3s", animationFillMode: "both" }}>
          +400.000 fuentes oficiales verificadas
        </p>
        <div className="mt-8 mx-auto h-[1px] gold-gradient animate-line-grow" style={{ maxWidth: "3rem" }} />
      </section>

      {/* ── Tool Cards Grid ──────────────────────────────────── */}
      <section className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6 stagger-children">
        {TOOLS.map((tool) => (
          <Link
            key={tool.href}
            href={tool.href}
            className="group bg-[var(--surface)] border border-[var(--outline-variant)] p-6 flex flex-col hover-lift hover:border-[var(--primary)]/40"
          >
            <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-[var(--muted)] mb-4 transition-colors duration-300 group-hover:text-[var(--primary)]">
              {tool.label}
            </span>
            <span
              className="text-2xl mb-3 transition-all duration-500 group-hover:scale-110"
              style={{ color: "var(--primary)", opacity: 0.35 }}
            >
              {tool.icon}
            </span>
            <h3 className="font-heading text-lg font-bold text-[var(--on-surface)] group-hover:text-[var(--primary)] transition-colors duration-300">
              {tool.title}
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-[var(--on-surface-variant)] flex-1">
              {tool.desc}
            </p>
            <div className="mt-5 h-[1px] w-0 group-hover:w-full gold-gradient transition-all duration-700 ease-out" />
          </Link>
        ))}
      </section>

      {/* ── Quote ────────────────────────────────────────────── */}
      <section className="text-center pb-8 animate-fade-in" style={{ animationDelay: "0.5s", animationFillMode: "both" }}>
        <p className="font-heading italic text-sm text-[var(--muted)] max-w-xl mx-auto leading-relaxed">
          &ldquo;The map is not the territory, but in the courtroom, the architecture of precedents is the only landscape that matters.&rdquo;
        </p>
      </section>
    </div>
  );
}
