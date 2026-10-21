-- Adds a source URL to onet_role_skills (where the skill's learning material / reference lives).
-- Nullable: existing rows have no source yet. When set, it must be an http(s) URL.

alter table public.onet_role_skills
    add column source text,
    add constraint onet_role_skills_source_is_url check (source is null or source ~ '^https?://\S+$');
