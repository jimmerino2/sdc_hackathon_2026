-- When a roadmap was built, so GET /roadmap can return a profile's most recent one without being told the role.
-- Roadmaps that already exist get the time this runs.
alter table public.roadmap add column created_at timestamptz not null default now();
