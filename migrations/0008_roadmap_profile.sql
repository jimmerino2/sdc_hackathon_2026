-- Roadmaps belong to a profile: each learner gets their own copy of a role's roadmap and their own progress.
-- 0003 made roadmap one row per role, before profiles existed. Those rows keep profile_id null: the backend only
-- reads roadmaps for a given profile, so they are ignored and can be deleted whenever convenient.
alter table public.roadmap drop constraint roadmap_onet_code_key;
alter table public.roadmap
    add column profile_id uuid references public.profiles (profile_id) on delete cascade;
alter table public.roadmap add constraint roadmap_profile_role_key unique (profile_id, onet_code);

-- Progress is now personal, so it is no longer publicly readable; only the backend's service role reads it.
drop policy "public read" on public.roadmap;
drop policy "public read" on public.roadmap_detail;
