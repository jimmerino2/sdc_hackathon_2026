-- Gives each roadmap node its own id, so one node can be addressed by a single value (POST /roadmap/complete/{id}).
-- Existing rows get a fresh uuid each. The primary key (roadmap_id, skill_id) is unchanged.
alter table public.roadmap_detail
    add column roadmap_detail_id uuid not null default gen_random_uuid() unique;
