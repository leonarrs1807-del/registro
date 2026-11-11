-- Run once in the Supabase SQL Editor as project owner.
-- Adapt an existing table explicitly if its schema differs; never drop its data.
create table if not exists public.licencias (
  id uuid primary key,
  app_id text not null,
  tipo_licencia text not null check (tipo_licencia in ('mensual','anual','perpetua')),
  hwid text,
  licencia_key text not null,
  fecha_emision timestamptz not null,
  fecha_expiracion timestamptz,
  estado text not null default 'activa' check (estado in ('activa','revocada')),
  idempotency_key text unique,
  request_hash text not null,
  created_at timestamptz not null default now(),
  check ((tipo_licencia = 'perpetua' and fecha_expiracion is null)
    or (tipo_licencia <> 'perpetua' and fecha_expiracion is not null and fecha_expiracion > fecha_emision))
);
alter table public.licencias enable row level security;
revoke all on public.licencias from anon, authenticated;
grant select, insert on public.licencias to service_role;
-- No browser policies: only the server's service key may access these records.
