create table public.profiles (
    profile_id  uuid primary key default gen_random_uuid(),
    email       text unique check (length(btrim(email)) > 0),
    name        text not null check (length(btrim(name)) > 0),
    stage       text not null check (stage in ('under', 'fresh', 'working')),
    concerns    text,
    skills      text[] not null default '{}',
    experience  jsonb  not null default '[]' check (jsonb_typeof(experience) = 'array'),
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create function public.set_profiles_updated_at() returns trigger
language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger profiles_set_updated_at
    before update on public.profiles
    for each row execute function public.set_profiles_updated_at();

-- Private: RLS on and no policies, so only the backend's service-role key can read or write.
alter table public.profiles enable row level security;
