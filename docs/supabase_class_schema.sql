-- Class management + approval flow + class files
-- Run in Supabase SQL editor

create extension if not exists pgcrypto;

create table if not exists public.classes (
  id uuid primary key default gen_random_uuid(),
  lecturer_id text not null,
  name text not null,
  code text not null unique,
  description text default '',
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_classes_lecturer_id on public.classes(lecturer_id);
create index if not exists idx_classes_code on public.classes(code);

create table if not exists public.class_members (
  id uuid primary key default gen_random_uuid(),
  class_id uuid not null references public.classes(id) on delete cascade,
  student_id text not null,
  status text not null check (status in ('pending', 'approved', 'rejected')) default 'pending',
  requested_at timestamptz not null default now(),
  approved_at timestamptz,
  approved_by text
);

create unique index if not exists uq_class_members_class_student
  on public.class_members(class_id, student_id);
create index if not exists idx_class_members_student_id on public.class_members(student_id);
create index if not exists idx_class_members_status on public.class_members(status);

create table if not exists public.class_files (
  file_id uuid primary key default gen_random_uuid(),
  class_id uuid not null references public.classes(id) on delete cascade,
  uploader_id text not null,
  original_filename text not null,
  stored_path text not null,
  size_bytes bigint not null,
  uploaded_at timestamptz not null default now()
);

create index if not exists idx_class_files_class_id on public.class_files(class_id);
create index if not exists idx_class_files_uploader_id on public.class_files(uploader_id);

-- Optional: keep legacy uploads table compatible with class scope
alter table if exists public.uploads
  add column if not exists visibility text not null default 'private'
  check (visibility in ('private', 'class'));

alter table if exists public.uploads
  add column if not exists class_id uuid references public.classes(id) on delete set null;

create index if not exists idx_uploads_class_id on public.uploads(class_id);
