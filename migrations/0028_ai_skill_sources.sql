-- Sources for AI skills (see 0027). Each AI skill keeps its own list of sources, so the one a role already has is reused with the
-- sources it was written with. A JSON array of {source_type, rank, title, url, duration_minutes}, the shape of a skill_sources row.
alter table public.onet_role_skills add column if not exists ai_sources jsonb not null default '[]';
