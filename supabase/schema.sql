create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text unique,
  full_name text,
  role text not null default 'user' check (role in ('user', 'admin')),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  plan_name text,
  status text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.subscriptions add column if not exists payment_provider text;
alter table public.subscriptions add column if not exists amount integer;
alter table public.subscriptions add column if not exists currency text;
alter table public.subscriptions add column if not exists payhero_reference text;
alter table public.subscriptions add column if not exists payhero_external_reference text;
alter table public.subscriptions add column if not exists payhero_checkout_request_id text;
alter table public.subscriptions add column if not exists payhero_provider_reference text;
alter table public.subscriptions add column if not exists payhero_phone_number text;
alter table public.subscriptions add column if not exists payhero_provider text;
alter table public.subscriptions add column if not exists payhero_channel_id bigint;
alter table public.subscriptions add column if not exists transaction_date timestamptz;
alter table public.subscriptions add column if not exists provider_payload jsonb;

create index if not exists subscriptions_user_id_idx on public.subscriptions (user_id);
create index if not exists subscriptions_status_idx on public.subscriptions (status);
create unique index if not exists subscriptions_payhero_reference_idx
  on public.subscriptions (payhero_reference)
  where payhero_reference is not null;
create unique index if not exists subscriptions_payhero_external_reference_idx
  on public.subscriptions (payhero_external_reference)
  where payhero_external_reference is not null;
create unique index if not exists subscriptions_payhero_checkout_request_id_idx
  on public.subscriptions (payhero_checkout_request_id)
  where payhero_checkout_request_id is not null;

alter table public.profiles enable row level security;
alter table public.subscriptions enable row level security;

drop policy if exists "Users can view their own profile" on public.profiles;
create policy "Users can view their own profile"
on public.profiles
for select
using (auth.uid() = id);

drop policy if exists "Users can update their own profile" on public.profiles;
create policy "Users can update their own profile"
on public.profiles
for update
using (auth.uid() = id);

drop policy if exists "Users can view their own subscriptions" on public.subscriptions;
create policy "Users can view their own subscriptions"
on public.subscriptions
for select
using (auth.uid() = user_id);

create or replace function public.handle_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists set_profiles_updated_at on public.profiles;
create trigger set_profiles_updated_at
before update on public.profiles
for each row
execute function public.handle_updated_at();

drop trigger if exists set_subscriptions_updated_at on public.subscriptions;
create trigger set_subscriptions_updated_at
before update on public.subscriptions
for each row
execute function public.handle_updated_at();
