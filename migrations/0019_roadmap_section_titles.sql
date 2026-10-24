-- Adds roadmap.section_titles: a jsonb array of the LLM's own title for each section (section N's title is
-- index N-1), e.g. ["Programming Fundamentals", "Web Development", "Cloud & Deployment"]. Null for a roadmap
-- built before this existed; the API treats a missing/short array as an untitled section rather than erroring.
--
-- The planner (src/backend/app/roadmap/planner.py) now groups skills by real subject-matter coherence instead
-- of a fixed foundations/core/applied/advanced template, and names each section itself, so the title has to be
-- stored per roadmap rather than derived from a fixed stage list.

alter table public.roadmap add column section_titles jsonb;
