-- The roles last suggested to a learner (the GET /jobs/recommend result), so the app can show them again
-- later without recomputing them (the AI matching step takes about half a minute).
alter table public.profiles
    add column suggested_roles jsonb,
    add column suggested_at    timestamptz;
