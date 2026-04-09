import type { Metadata } from "next";
import { Newsreader, Inter } from "next/font/google";
import Link from "next/link";
import { NavLinks } from "@/components/nav-links";
import "./globals.css";

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-newsreader",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "LITIGIA — Institutional Grade Legal Tech",
  description: "Jurisprudencia, escritos y analisis para abogados argentinos",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className={`${newsreader.variable} ${inter.variable}`}>
      <body className="min-h-screen flex flex-col">
        {/* ── Nav ─────────────────────────────────────────────── */}
        <header className="sticky top-0 z-50 bg-[var(--bg)]/95 backdrop-blur-md border-b border-[var(--outline-variant)]/30">
          <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-4 group">
              <div className="w-10 h-10 flex items-center justify-center border border-[var(--primary-container)] group-hover:border-[var(--primary)] transition-colors">
                <span className="font-heading text-[var(--primary)] font-bold text-lg">L</span>
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-[0.2em] text-[var(--on-surface)]">LITIGIA</h1>
                <p className="text-[9px] tracking-[0.3em] uppercase text-[var(--primary-container)] opacity-70">
                  Institutional Grade Legal Tech
                </p>
              </div>
            </Link>

            {/* Nav Links */}
            <NavLinks />

            {/* Settings */}
            <svg
              className="w-5 h-5 text-[var(--muted)] hover:text-[var(--primary)] transition-colors cursor-pointer"
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
          </div>
        </header>

        {/* ── Main ────────────────────────────────────────────── */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-8 py-10">
          {children}
        </main>

        {/* ── Footer ──────────────────────────────────────────── */}
        <footer className="border-t border-[var(--outline-variant)]/20 bg-[var(--bg)]">
          <div className="max-w-7xl mx-auto px-8 py-6 flex items-center justify-between">
            <div>
              <span className="font-heading text-sm italic text-[var(--primary-container)]">Litigia</span>
              <span className="text-[10px] tracking-[0.15em] uppercase text-[var(--muted)] ml-3">
                Institutional Grade Legal Tech
              </span>
            </div>
            <div className="flex gap-6 text-[11px] tracking-wide uppercase text-[var(--muted)]">
              <span className="hover:text-[var(--primary)] transition-colors cursor-pointer">Privacy</span>
              <span className="hover:text-[var(--primary)] transition-colors cursor-pointer">Terms</span>
              <span className="hover:text-[var(--primary)] transition-colors cursor-pointer">Documentation</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
