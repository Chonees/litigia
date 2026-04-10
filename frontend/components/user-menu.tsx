"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function UserMenu() {
  const { user, loading, signOut } = useAuth();
  const [showMenu, setShowMenu] = useState(false);

  if (loading || !user) return null;

  const initial = (user.user_metadata?.full_name?.[0] ?? user.email?.[0] ?? "U").toUpperCase();

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="w-9 h-9 flex items-center justify-center border border-[var(--primary-container)] text-[var(--primary)] font-heading font-bold text-sm transition-all duration-300 hover:border-[var(--primary)] hover:shadow-sm"
      >
        {initial}
      </button>

      {showMenu && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setShowMenu(false)} />
          <div className="absolute right-0 top-12 z-50 w-56 bg-[var(--surface)] border border-[var(--outline-variant)] shadow-lg animate-slide-down">
            <div className="p-4 border-b border-[var(--outline-variant)]">
              <p className="text-xs font-semibold text-[var(--on-surface)] truncate">
                {user.user_metadata?.full_name ?? "Usuario"}
              </p>
              <p className="text-[10px] text-[var(--muted)] truncate mt-0.5">{user.email}</p>
            </div>
            <div className="p-2">
              <Link
                href="/guardados"
                onClick={() => setShowMenu(false)}
                className="block px-3 py-2 text-xs text-[var(--on-surface)] hover:bg-[var(--container-lowest)] transition-colors"
              >
                Mis guardados
              </Link>
              <button
                onClick={() => { signOut(); setShowMenu(false); }}
                className="w-full text-left px-3 py-2 text-xs text-[var(--danger)] hover:bg-[var(--container-lowest)] transition-colors"
              >
                Cerrar sesión
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
