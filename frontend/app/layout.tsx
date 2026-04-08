import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LITIGIA — Asistente Legal IA",
  description: "Jurisprudencia, escritos y analisis para abogados argentinos",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body className="min-h-screen">
        <header className="bg-[var(--color-primary)] text-white shadow-lg">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-[var(--color-accent)] flex items-center justify-center font-bold text-[var(--color-primary)] text-lg">
                L
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-wide leading-tight">
                  LITIGIA
                </h1>
                <p className="text-[var(--color-accent)] text-xs tracking-widest uppercase">
                  Asistente Legal IA
                </p>
              </div>
            </div>
            <nav className="flex items-center gap-4 text-sm">
              <span className="px-3 py-1 rounded-full bg-[var(--color-success)] text-white text-xs font-medium">
                Online
              </span>
            </nav>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
        <footer className="border-t border-[var(--color-border)] mt-12">
          <div className="max-w-7xl mx-auto px-6 py-4 text-center text-xs text-[var(--color-text-muted)]">
            LITIGIA v0.1 — Los resultados son orientativos. Siempre verificar con fuentes oficiales.
          </div>
        </footer>
      </body>
    </html>
  );
}
