-- AI skills: each roadmap section gets one skill that teaches how to use AI to learn that section's skills.
-- They are stored as ordinary onet_role_skills rows, told apart by skill_origin, so a roadmap's node for one is an
-- ordinary roadmap_detail row (progress, prerequisites and unlocking work as for any skill).
--   skill_origin   'traditional' = from O*NET (and everything that existed before); 'ai' = written by the model for a role.
--   ai_description what the AI skill is about, in plain words.
--   ai_steps       a JSON array of short things to do, in order.
-- An AI skill is inserted only if the role does not have it yet (same title, ignoring case and spacing), so a skill the
-- model already wrote for a role is reused by the next learner's roadmap, not written again.
-- AI skills have no importance or level, so every reader that only considers skills above an importance cut-off
-- (the roadmap planner, the challenge generator) never sees them.
-- Roadmaps built before this have no AI skills until they are rebuilt.
alter table public.onet_role_skills add column if not exists skill_origin text not null default 'traditional'
    check (skill_origin in ('traditional', 'ai'));
alter table public.onet_role_skills add column if not exists ai_description text;
alter table public.onet_role_skills add column if not exists ai_steps jsonb not null default '[]';

create unique index if not exists onet_role_skills_ai_name_idx
    on public.onet_role_skills (onet_code, lower(skill_name)) where skill_origin = 'ai';
