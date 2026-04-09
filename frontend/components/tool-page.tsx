"use client";

import { useState } from "react";
import { SectionHeader, GoldButton } from "@/components/ui";

interface ToolPageProps {
  label: string;
  title: string;
  buttonText: string;
  children: React.ReactNode;
  onSubmit: (data: Record<string, string>) => Promise<Record<string, unknown>>;
  renderResult: (result: Record<string, unknown>) => React.ReactNode;
}

export function ToolPage({
  label,
  title,
  buttonText,
  children,
  onSubmit,
  renderResult,
}: ToolPageProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data = Object.fromEntries(formData.entries()) as Record<string, string>;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await onSubmit(data);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de conexión con el servidor");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-enter space-y-8">
      <form onSubmit={handleSubmit} className="space-y-6">
        <SectionHeader label={label} title={title} />
        <div className="animate-fade-in" style={{ animationDelay: "0.1s", animationFillMode: "both" }}>
          {children}
        </div>
        <div className="animate-fade-in" style={{ animationDelay: "0.2s", animationFillMode: "both" }}>
          <GoldButton disabled={loading}>
            {loading ? <span className="animate-pulse-slow">Procesando...</span> : buttonText}
          </GoldButton>
        </div>
      </form>

      {error && (
        <div className="bg-[var(--danger-container)] border-l-2 border-[var(--danger)] p-4 animate-scale-in">
          <p className="text-sm text-[var(--danger)]">{error}</p>
        </div>
      )}

      {result && (
        <div className="animate-slide-up">
          {renderResult(result)}
        </div>
      )}
    </div>
  );
}
