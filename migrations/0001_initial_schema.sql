-- Initial schema for the reference tables the app reads at runtime.
-- Source of truth for columns: data/documentation/STRUCTURE.md
-- Load order matters (foreign keys): onet_roles first, then the rest.
-- Data comes from data/processed/*.csv. Blank CSV cells must be loaded as NULL.
-- Not included yet: forecast_output (shape not agreed, see SUPABASE_INTEGRATION.md).

-- ---------------------------------------------------------------------------
-- onet_roles: the 46 roles (role list + descriptions)
-- ---------------------------------------------------------------------------
create table public.onet_roles (
    onet_code   text primary key,          -- e.g. '11-2021.00' (text: has a dot)
    title       text not null,
    job_zone    smallint,
    description text
);

-- ---------------------------------------------------------------------------
-- onet_role_skills: skills per role (Screens 4-5)
-- level is NULL for all software rows.
-- ---------------------------------------------------------------------------
create table public.onet_role_skills (
    onet_code   text not null references public.onet_roles (onet_code),
    skill_id    text not null,
    skill_name  text not null,
    skill_type  text not null,
    importance  real,
    level       real,
    primary key (onet_code, skill_id)
);

-- ---------------------------------------------------------------------------
-- ai_exposure: Y-axis of the quadrant (Screen 4)
-- automation_share / augmentation_share are NULL for 3 jobs.
-- Wind Turbine Service Technicians (49-9081.00) has exposure 0.000 as a
-- fallback (missing from the source), so the app should show "no data".
-- ---------------------------------------------------------------------------
create table public.ai_exposure (
    onet_code           text primary key references public.onet_roles (onet_code),
    title               text not null,
    exposure            real,
    automation_share    real,
    augmentation_share  real,
    source              text,
    as_of_date          date
);

-- ---------------------------------------------------------------------------
-- ai_exposure_detail: raw Anthropic Economic Index data, 746 occupations
-- Superset of ai_exposure, so no foreign key to onet_roles.
-- Many metric columns are NULL for low-usage occupations.
-- ---------------------------------------------------------------------------
create table public.ai_exposure_detail (
    onet_code                                         text primary key,
    title                                             text not null,
    pct_claude_ai                                     real,
    collaboration_bucket_automation_pct_claude_ai     real,
    collaboration_bucket_augmentation_pct_claude_ai   real,
    use_case_work_pct_claude_ai                       real,
    ai_autonomy_mean_claude_ai                        real,
    pct_api                                           real,
    collaboration_bucket_automation_pct_api           real,
    collaboration_bucket_augmentation_pct_api         real,
    use_case_work_pct_api                             real,
    ai_autonomy_mean_api                              real,
    work_pct_claude_ai                                real,
    work_pct_api                                      real,
    usage_share                                       real,
    exposure                                          real,
    automation_share                                  real,
    augmentation_share                                real,
    low_sample                                        boolean,
    release                                           date
);

-- ---------------------------------------------------------------------------
-- crosswalk: role -> Indeed sector(s). Weights sum to 1 per job.
-- indeed_sector joins to forecast_output.sector once that table exists.
-- ---------------------------------------------------------------------------
create table public.crosswalk (
    onet_code      text not null references public.onet_roles (onet_code),
    title          text,
    indeed_sector  text not null,
    weight         real not null,
    rationale      text,
    primary key (onet_code, indeed_sector)
);

-- ---------------------------------------------------------------------------
-- onet_to_my_group: role -> Malaysian occupation group
-- ---------------------------------------------------------------------------
create table public.onet_to_my_group (
    onet_code            text primary key references public.onet_roles (onet_code),
    title                text,
    my_occupation_group  text not null,
    rationale            text
);

-- ---------------------------------------------------------------------------
-- my_vacancies: DOSM online job vacancies. DISPLAY ONLY.
-- Raw counts, not an index; totals jump ~2x in 2021-Q3 and 2025-Q3, so never
-- compare across those quarters. 2026 is partial (Jan-Jun).
-- period is text: '2019-07' (month), quarter label, or '2025' (year) by freq.
-- ---------------------------------------------------------------------------
create table public.my_vacancies (
    freq        text not null check (freq in ('month', 'quarter', 'year')),
    period      text not null,
    group_type  text not null check (group_type in ('industry', 'occupation')),
    "group"     text not null,
    vacancies   integer,
    is_partial  boolean not null default false,
    source      text,
    source_url  text,
    as_of_date  date,
    primary key (freq, period, group_type, "group")
);

-- ---------------------------------------------------------------------------
-- Row Level Security: public reference data, read-only for the anon key.
-- No insert/update/delete policies exist, so only the service role can write.
-- ---------------------------------------------------------------------------
alter table public.onet_roles          enable row level security;
alter table public.onet_role_skills    enable row level security;
alter table public.ai_exposure         enable row level security;
alter table public.ai_exposure_detail  enable row level security;
alter table public.crosswalk           enable row level security;
alter table public.onet_to_my_group    enable row level security;
alter table public.my_vacancies        enable row level security;

create policy "public read" on public.onet_roles          for select to anon, authenticated using (true);
create policy "public read" on public.onet_role_skills    for select to anon, authenticated using (true);
create policy "public read" on public.ai_exposure         for select to anon, authenticated using (true);
create policy "public read" on public.ai_exposure_detail  for select to anon, authenticated using (true);
create policy "public read" on public.crosswalk           for select to anon, authenticated using (true);
create policy "public read" on public.onet_to_my_group    for select to anon, authenticated using (true);
create policy "public read" on public.my_vacancies        for select to anon, authenticated using (true);
