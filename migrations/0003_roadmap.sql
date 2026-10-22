-- Roadmap structure: a role's skills laid out in sections and units, with prerequisites and progress.
--   roadmap         ONE row per role. section/unit are the learner's CURRENT step; status is the whole roadmap's.
--   roadmap_detail  the skill nodes. Each node says which section and unit it sits in.
-- Needs 0001 (onet_roles, onet_role_skills). Tables start empty.

create table public.roadmap (
    roadmap_id  uuid primary key default gen_random_uuid(),
    onet_code   text not null unique references public.onet_roles (onet_code),
    -- Current step: where the learner is now.
    section     int  not null default 1 check (section >= 1),
    unit        int  not null default 1 check (unit >= 1),
    -- locked: not reachable yet; available: can start; in_progress: some nodes completed; completed: all done
    status      text not null default 'locked'
                    check (status in ('locked', 'available', 'in_progress', 'completed')),
    unique (roadmap_id, onet_code)         -- lets roadmap_detail tie its skill to the same role
);

create table public.roadmap_detail (
    roadmap_id              uuid not null,
    onet_code               text not null,
    skill_id                text not null,
    -- Where this node sits in the roadmap.
    section                 int  not null check (section >= 1),
    unit                    int  not null check (unit >= 1),
    status                  text not null default 'locked'
                                check (status in ('locked', 'available', 'completed')),
    completed_at            timestamptz,
    -- skill_ids (same onet_code) that come before this node. No FK: Postgres cannot enforce array elements.
    previous_nodes          text[] not null default '{}',
    -- true: all previous_nodes must be completed to unlock this node; false: they are only suggested
    previous_nodes_required boolean not null default true,
    primary key (roadmap_id, skill_id),
    foreign key (roadmap_id, onet_code) references public.roadmap (roadmap_id, onet_code) on delete cascade,
    foreign key (onet_code, skill_id)   references public.onet_role_skills (onet_code, skill_id),
    check ((status = 'completed') = (completed_at is not null)),
    check (not skill_id = any (previous_nodes))
);

create index roadmap_detail_location_idx on public.roadmap_detail (roadmap_id, section, unit);
create index roadmap_detail_skill_idx    on public.roadmap_detail (onet_code, skill_id);

-- Public read-only for the anon key, like the other tables. No write policies: only the service role writes.
alter table public.roadmap        enable row level security;
alter table public.roadmap_detail enable row level security;

create policy "public read" on public.roadmap        for select to anon, authenticated using (true);
create policy "public read" on public.roadmap_detail for select to anon, authenticated using (true);
