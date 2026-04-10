"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

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

  return (
    <nav className="flex items-center gap-1">
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
            {!isActive && (
              <span className="absolute bottom-0 left-2 right-2 h-[2px] bg-[var(--primary)] scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left" />
            )}
          </Link>
        );
      })}
    </nav>
  );
}
