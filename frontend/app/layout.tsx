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
        <header className="bg-black/90 backdrop-blur-md border-b border-[var(--color-border)]">
          <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded border border-[var(--color-accent)] flex items-center justify-center">
                <span className="text-[var(--color-accent)] font-bold text-lg">L</span>
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-[0.2em] text-white">
                  LITIGIA
                </h1>
                <p className="text-[10px] tracking-[0.3em] uppercase text-[var(--color-accent)]" style={{opacity: 0.7}}>
                  Asistente Legal IA
                </p>
              </div>
            </div>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-6 py-8 pb-16">{children}</main>
        <footer className="fixed bottom-0 left-0 right-0 bg-black/90 backdrop-blur-md border-t border-[var(--color-border)] z-50">
          <div className="max-w-7xl mx-auto px-6 py-4 text-center text-xs text-[var(--color-accent)]" style={{opacity: 0.5}}>
            +400.000 fuentes oficiales verificadas
          </div>
        </footer>
      </body>
    </html>
  );
}
