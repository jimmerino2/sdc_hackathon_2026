-- AI skills now come from a fixed list in code (src/backend/app/roadmap/ai_skills.py): their steps and their YouTube videos are fixed
-- there, and only the one line written for the role is stored (onet_role_skills.ai_description). So the two columns that held the
-- steps and the sources are not needed. Safe to run whether or not 0027 added them (and 0028, which was dropped, never did).
-- Run 0029 (the temporary clean-up) before roadmaps are rebuilt, so no AI skill written by the older version is left in a roadmap.
alter table public.onet_role_skills drop column if exists ai_steps;
alter table public.onet_role_skills drop column if exists ai_sources;
