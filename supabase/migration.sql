-- ═══════════════════════════════════════════════════════════════════
-- LITIGIA — Supabase Schema Migration
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- ═══════════════════════════════════════════════════════════════════

-- 1. Profiles (extends auth.users)
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  created_at timestamptz default now()
);

-- 2. Saved items (generic store for all tool outputs)
create table if not exists public.saved_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  type text not null check (type in ('jurisprudencia', 'escrito', 'resumen', 'oficio', 'analisis')),
  title text not null,
  data jsonb not null,
  created_at timestamptz default now()
);

-- 3. Indexes
create index if not exists idx_saved_items_user on public.saved_items(user_id);
create index if not exists idx_saved_items_type on public.saved_items(user_id, type);
create index if not exists idx_saved_items_created on public.saved_items(user_id, created_at desc);

-- 4. RLS
alter table public.profiles enable row level security;
alter table public.saved_items enable row level security;

-- Profiles
create policy "Users can view own profile"
  on public.profiles for select using (auth.uid() = id);
create policy "Users can update own profile"
  on public.profiles for update using (auth.uid() = id);

-- Saved items
create policy "Users can view own items"
  on public.saved_items for select using (auth.uid() = user_id);
create policy "Users can insert own items"
  on public.saved_items for insert with check (auth.uid() = user_id);
create policy "Users can delete own items"
  on public.saved_items for delete using (auth.uid() = user_id);

-- 5. Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (new.id, new.email, new.raw_user_meta_data->>'full_name');
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
