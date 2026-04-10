"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { Label, Input, GoldButton } from "@/components/ui";

export function AuthPage() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const err = await signIn(email, password);
    setLoading(false);
    if (err) setError(err);
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-md page-enter">
        {/* Logo + Branding */}
        <div className="text-center mb-12">
          <div className="w-16 h-16 mx-auto flex items-center justify-center border border-[var(--primary-container)] mb-6">
            <span className="font-heading text-[var(--primary)] font-bold text-3xl">L</span>
          </div>
          <h1 className="font-heading text-4xl font-bold text-[var(--on-surface)] tracking-tight">
            LITIGIA
          </h1>
          <p className="mt-2 text-[11px] tracking-[0.3em] uppercase text-[var(--muted)]">
            Institutional Grade Legal Tech
          </p>
          <div className="mt-4 mx-auto h-[1px] gold-gradient animate-line-grow" style={{ maxWidth: "3rem" }} />
        </div>

        {/* Login Form */}
        <form
          onSubmit={handleSubmit}
          className="bg-[var(--surface)] border border-[var(--outline-variant)] p-8 space-y-6 animate-fade-in"
        >
          <h2 className="font-heading text-xl font-bold text-[var(--on-surface)] text-center">
            Ingresar
          </h2>

          <div>
            <Label>Email</Label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="email@estudio.com.ar"
              required
            />
          </div>

          <div>
            <Label>Contraseña</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <p className="text-xs text-[var(--danger)] animate-fade-in">{error}</p>
          )}

          <GoldButton disabled={loading}>
            {loading ? "Procesando..." : "Ingresar"}
          </GoldButton>
        </form>

        <p className="mt-8 text-center font-heading italic text-xs text-[var(--muted)] animate-fade-in" style={{ animationDelay: "0.4s", animationFillMode: "both" }}>
          +400.000 fuentes oficiales verificadas
        </p>
      </div>
    </div>
  );
}
