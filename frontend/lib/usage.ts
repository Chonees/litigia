import { supabase } from "@/lib/supabase";

export interface UsageLog {
  id: string;
  tool: string;
  tier: string | null;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  reader_model: string | null;
  synth_model: string | null;
  fallos_analyzed: number;
  duration_seconds: number;
  created_at: string;
}

export async function logUsage(data: {
  tool: string;
  tier?: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  reader_model?: string;
  synth_model?: string;
  fallos_analyzed?: number;
  duration_seconds?: number;
}) {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return;

  await supabase.from("usage_logs").insert({
    user_id: user.id,
    ...data,
  });
}

export async function getUsageLogs(): Promise<UsageLog[]> {
  const { data, error } = await supabase
    .from("usage_logs")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(100);

  if (error) throw new Error(error.message);
  return (data ?? []) as UsageLog[];
}

export async function getUsageSummary(): Promise<{
  total_cost: number;
  total_analyses: number;
  by_tier: Record<string, { count: number; cost: number }>;
}> {
  const logs = await getUsageLogs();

  const total_cost = logs.reduce((sum, l) => sum + l.cost_usd, 0);
  const total_analyses = logs.length;
  const by_tier: Record<string, { count: number; cost: number }> = {};

  for (const log of logs) {
    const tier = log.tier || "premium";
    if (!by_tier[tier]) by_tier[tier] = { count: 0, cost: 0 };
    by_tier[tier].count++;
    by_tier[tier].cost += log.cost_usd;
  }

  return { total_cost, total_analyses, by_tier };
}
