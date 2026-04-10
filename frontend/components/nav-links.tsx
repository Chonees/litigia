"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

const NAV_ITEMS = [
  { href: "/jurisprudencia", label: "Jurisprudencia" },
  { href: "/escrito", label: "Escrito" },
  { href: "/resumen", label: "Resumen" },
  { href: "/oficio", label: "Oficio" },
  { href: "/analisis", label: "Análisis" },
  { href: "/guardados", label: "Guardados" },
];

export function NavLinks() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // Close menu on route change
  useEffect(() => { setOpen(false); }, [pathname]);

  return (
    <>
      {/* Desktop nav */}
      <nav className="hidden lg:flex items-center gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`relative px-4 py-2 text-xs tracking-[0.1em] uppercase font-medium transition-all duration-300 hover:scale-[1.02] ${
                isActive
                  ? "text-[var(--primary)]"
                  : "text-[var(--muted)] hover:text-[var(--on-surface)]"
              }`}
            >
              {item.label}
              {isActive && (
                <span className="absolute bottom-0 left-2 right-2 h-[2px] gold-gradient animate-line-grow" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Mobile hamburger */}
      <button
        className="lg:hidden flex flex-col justify-center items-center w-9 h-9 gap-[5px]"
        onClick={() => setOpen(o => !o)}
        aria-label="Menu"
      >
        <span className={`block w-5 h-[1.5px] bg-[var(--on-surface)] transition-all duration-200 ${open ? "translate-y-[6.5px] rotate-45" : ""}`} />
        <span className={`block w-5 h-[1.5px] bg-[var(--on-surface)] transition-all duration-200 ${open ? "opacity-0" : ""}`} />
        <span className={`block w-5 h-[1.5px] bg-[var(--on-surface)] transition-all duration-200 ${open ? "-translate-y-[6.5px] -rotate-45" : ""}`} />
      </button>

      {/* Mobile dropdown */}
      {open && (
        <div className="lg:hidden absolute top-full left-0 right-0 bg-[var(--bg)] border-b border-[var(--outline-variant)]/30 shadow-sm z-50">
          <nav className="max-w-7xl mx-auto px-4 py-3 flex flex-col">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className={`px-3 py-3 text-xs tracking-[0.1em] uppercase font-medium border-b border-[var(--outline-variant)]/10 last:border-b-0 ${
                    isActive
                      ? "text-[var(--primary)]"
                      : "text-[var(--muted)]"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      )}
    </>
  );
}
