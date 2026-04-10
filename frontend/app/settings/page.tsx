"use client";

import { useEffect, useState } from "react";
import { SectionHeader, Card, CardHeader, StatBox } from "@/components/ui";
import { getUsageLogs, getUsageSummary, type UsageLog } from "@/lib/usage";

const TIER_LABELS: Record<string, { name: string; color: string }> = {
  premium: { name: "Premium", color: "var(--primary)" },
  standard: { name: "Standard", color: "var(--on-surface-variant)" },
  economy: { name: "Economy", color: "var(--muted)" },
};

export default function SettingsPage() {
  const [logs, setLogs] = useState<UsageLog[]>([]);
  const [summary, setSummary] = useState<{
    total_cost: number;
    total_analyses: number;
    by_tier: Record<string, { count: number; cost: number }>;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getUsageLogs(), getUsageSummary()])
      .then(([logs, summary]) => {
        setLogs(logs);
        setSummary(summary);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-enter space-y-8">
      <SectionHeader label="Configuration" title="Settings" />

      {/* Tier Reference */}
      <div>
        <CardHeader>Tiers de Análisis</CardHeader>
        <div className="grid grid-cols-3 gap-1">
          <Card accent="gold">
            <h4 className="font-heading font-bold text-sm text-[var(--primary)]">Premium</h4>
            <p className="text-[11px] text-[var(--muted)] mt-1">Sonnet readers + Opus synthesis</p>
            <p className="text-lg font-heading font-bold text-[var(--on-surface)] mt-2">~$2.70</p>
            <p className="text-[10px] text-[var(--muted)]">por análisis</p>
          </Card>
          <Card>
            <h4 className="font-heading font-bold text-sm text-[var(--on-surface-variant)]">Standard</h4>
            <p className="text-[11px] text-[var(--muted)] mt-1">Haiku readers + Opus synthesis</p>
            <p className="text-lg font-heading font-bold text-[var(--on-surface)] mt-2">~$0.55</p>
            <p className="text-[10px] text-[var(--muted)]">por análisis</p>
          </Card>
          <Card>
            <h4 className="font-heading font-bold text-sm text-[var(--muted)]">Economy</h4>
            <p className="text-[11px] text-[var(--muted)] mt-1">Haiku readers + Sonnet synthesis</p>
            <p className="text-lg font-heading font-bold text-[var(--on-surface)] mt-2">~$0.20</p>
            <p className="text-[10px] text-[var(--muted)]">por análisis</p>
          </Card>
        </div>
      </div>

      {/* Usage Summary */}
      {loading ? (
        <div className="text-center py-8 animate-pulse-slow text-[var(--muted)]">Cargando...</div>
      ) : summary ? (
        <>
          <div>
            <CardHeader>Consumo Total</CardHeader>
            <div className="grid grid-cols-3 gap-1">
              <StatBox
                value={`$${summary.total_cost.toFixed(2)}`}
                label="Gasto Total USD"
                variant="gold"
                large
              />
              <StatBox
                value={summary.total_analyses}
                label="Análisis Realizados"
              />
              <StatBox
                value={summary.total_analyses > 0 ? `$${(summary.total_cost / summary.total_analyses).toFixed(2)}` : "$0.00"}
                label="Promedio por Análisis"
              />
            </div>
          </div>

          {/* By Tier */}
          {Object.keys(summary.by_tier).length > 0 && (
            <div>
              <CardHeader>Consumo por Tier</CardHeader>
              <div className="grid grid-cols-3 gap-1">
                {Object.entries(summary.by_tier).map(([tier, data]) => (
                  <Card key={tier}>
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] uppercase tracking-wide font-medium" style={{ color: TIER_LABELS[tier]?.color || "var(--muted)" }}>
                        {TIER_LABELS[tier]?.name || tier}
                      </span>
                      <span className="text-xs text-[var(--muted)]">{data.count} análisis</span>
                    </div>
                    <p className="text-lg font-heading font-bold text-[var(--on-surface)] mt-1">
                      ${data.cost.toFixed(4)}
                    </p>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Usage Log */}
          {logs.length > 0 && (
            <div>
              <CardHeader>Historial de Uso</CardHeader>
              <div className="space-y-1">
                {logs.map((log) => {
                  const tierCfg = TIER_LABELS[log.tier || "premium"];
                  return (
                    <div key={log.id} className="flex items-center justify-between px-4 py-3 bg-[var(--surface)] border border-[var(--outline-variant)]/50 text-[11px]">
                      <div className="flex items-center gap-4">
                        <span className="uppercase tracking-wide font-medium" style={{ color: tierCfg?.color }}>
                          {tierCfg?.name || log.tier}
                        </span>
                        <span className="text-[var(--muted)]">
                          {new Date(log.created_at).toLocaleDateString("es-AR", {
                            day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
                          })}
                        </span>
                        <span className="text-[var(--muted)]">
                          {log.input_tokens.toLocaleString()} in / {log.output_tokens.toLocaleString()} out
                        </span>
                        {log.fallos_analyzed > 0 && (
                          <span className="text-[var(--muted)]">{log.fallos_analyzed} fallos</span>
                        )}
                      </div>
                      <span className="font-bold text-[var(--primary)]">
                        ${log.cost_usd.toFixed(4)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-8 text-[var(--muted)]">No hay datos de uso todavía.</div>
      )}
    </div>
  );
}
