-- ═══════════════════════════════════════════════════════════════════
-- LITIGIA — Usage Tracking Migration
-- Run in Supabase SQL Editor after the initial migration
-- ═══════════════════════════════════════════════════════════════════

create table if not exists public.usage_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  tool text not null check (tool in ('jurisprudencia', 'escrito', 'resumen', 'oficio', 'analisis')),
  tier text check (tier in ('premium', 'standard', 'economy')),
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  cost_usd numeric(10, 6) not null default 0,
  reader_model text,
  synth_model text,
  fallos_analyzed integer default 0,
  duration_seconds integer default 0,
  created_at timestamptz default now()
);

create index if not exists idx_usage_user on public.usage_logs(user_id);
create index if not exists idx_usage_created on public.usage_logs(user_id, created_at desc);

alter table public.usage_logs enable row level security;

create policy "Users can view own usage"
  on public.usage_logs for select using (auth.uid() = user_id);
create policy "Users can insert own usage"
  on public.usage_logs for insert with check (auth.uid() = user_id);
