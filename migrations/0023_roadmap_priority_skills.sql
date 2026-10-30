-- Skills a learner chose to focus on in the What-If simulator. Their roadmap's order is arranged around these, so
-- a roadmap with priority skills must not be the plan other learners' roadmaps are copied from.
alter table roadmap add column if not exists priority_skills text[] not null default '{}';
