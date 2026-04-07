import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LITIGIA — Asistente Legal IA",
  description: "Jurisprudencia, escritos y análisis para abogados argentinos",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body className="min-h-screen">
        <header className="bg-[var(--color-primary)] text-white py-4 px-6 shadow-lg">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <h1 className="text-2xl font-bold tracking-wide">
              LITIGIA
              <span className="text-[var(--color-accent)] ml-2 text-sm font-normal">
                Asistente Legal IA
              </span>
            </h1>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
