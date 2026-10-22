-- profiles.skills goes from plain names to [{"name": ..., "score": 0-1}], so job matching knows how strong each skill is.
-- Names are O*NET skill names. Existing names are kept with a neutral score of 0.5.
alter table public.profiles add column skills_scored jsonb not null default '[]'
    check (jsonb_typeof(skills_scored) = 'array');

update public.profiles as p
set skills_scored = coalesce(
    (select jsonb_agg(jsonb_build_object('name', s, 'score', 0.5)) from unnest(p.skills) as s),
    '[]'
);

alter table public.profiles drop column skills;
alter table public.profiles rename column skills_scored to skills;
