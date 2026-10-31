-- The UN SDG targets (sub-goals, e.g. 8.2) each role and each skill serves, from data/processed/onet_roles_sdg.csv
-- and onet_skills_sdg.csv. One main goal, the other relevant goals, and the targets as a jsonb array of
-- {"code": "8.2", "sdg": 8, "text": "productivity through market innovation and commercialization"}.
-- onet_roles.sdg (0014) keeps the weights the matching uses; these tables say which targets the work serves, for the
-- role page. Filled by pipeline/load_supabase.py --tables onet_roles_sdg onet_skills_sdg.

create table public.onet_roles_sdg (
    onet_code     text    primary key references public.onet_roles (onet_code) on delete cascade,
    main_sdg      int     not null check (main_sdg between 1 and 17),
    relevant_sdgs int[]   not null default '{}' check (relevant_sdgs <@ array[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]),
    targets       jsonb   not null default '[]' check (jsonb_typeof(targets) = 'array')
);

-- Keyed by O*NET element id (onet_role_skills.skill_id): skills, knowledge areas and tech tools.
create table public.onet_skills_sdg (
    skill_id      text    primary key,
    skill_name    text    not null,
    skill_type    text    not null check (skill_type in ('skill', 'knowledge', 'tech')),
    main_sdg      int     not null check (main_sdg between 1 and 17),
    relevant_sdgs int[]   not null default '{}' check (relevant_sdgs <@ array[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]),
    targets       jsonb   not null default '[]' check (jsonb_typeof(targets) = 'array')
);

-- Public reference data, like onet_roles: read-only for the anon key, written by the service role.
alter table public.onet_roles_sdg  enable row level security;
alter table public.onet_skills_sdg enable row level security;
create policy "public read" on public.onet_roles_sdg  for select to anon, authenticated using (true);
create policy "public read" on public.onet_skills_sdg for select to anon, authenticated using (true);
