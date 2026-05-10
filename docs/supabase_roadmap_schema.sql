-- Roadmap persistence schema
-- Run in Supabase SQL editor

create table if not exists public.roadmap_plans (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  mode text not null default 'v2',
  summary text,
  next_action_item_id text,
  generated_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_roadmap_plans_user_id on public.roadmap_plans(user_id);
create index if not exists idx_roadmap_plans_generated_at on public.roadmap_plans(generated_at desc);

create table if not exists public.roadmap_items (
  id uuid primary key default gen_random_uuid(),
  plan_id uuid not null references public.roadmap_plans(id) on delete cascade,
  item_key text not null,
  topic text not null,
  description text not null,
  priority text not null check (priority in ('high','medium','low')),
  eta_minutes int not null default 30,
  progress int not null default 0 check (progress >= 0 and progress <= 100),
  status text not null default 'todo' check (status in ('todo','doing','done')),
  sources jsonb not null default '[]'::jsonb,
  actions jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(plan_id, item_key)
);

create index if not exists idx_roadmap_items_plan_id on public.roadmap_items(plan_id);
create index if not exists idx_roadmap_items_status on public.roadmap_items(status);
