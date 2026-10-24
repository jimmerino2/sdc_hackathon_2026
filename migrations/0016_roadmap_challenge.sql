-- Bonus Quests: an optional project after every two sections of a roadmap, built from the skills of those sections
-- and themed on one of the learner's SDGs (through their interests). The learner submits a public GitHub repo and
-- the LLM scores it against the challenge's rubric. Only the tech roles get challenges (jobs.service.TECH_ROLES).
--
-- Written once by POST /roadmap, per roadmap (unlike the plan, it depends on the learner, so it is never copied).
-- Sections are paired 1-2, 3-4; with an odd count the last section joins the final challenge (3 sections -> one
-- challenge over 1-3). Whether a challenge is locked is not stored: it is open once every node in its sections is
-- completed, and it never blocks later sections.
--
-- tech_stack is a jsonb array of {"area": "Frontend", "skills": ["<O*NET skill_name>", ...]}.
-- rubric is a jsonb array of {"key": "c1", "criterion": "...", "description": "...", "weight": <int>}, weights adding
-- up to 100. result is a jsonb array of {"key": "c1", "score": <0-100>, "why": "...", "improve": "..."}, one per
-- rubric key; score is the weighted total. There is no pass or fail, only the score and the reasoning.
-- Only the latest submission is kept; attempts counts them.

create table public.roadmap_challenge (
    challenge_id  uuid primary key default gen_random_uuid(),
    roadmap_id    uuid not null references public.roadmap (roadmap_id) on delete cascade,
    sections      int[] not null check (cardinality(sections) >= 1),  -- the sections it covers; shown after the last
    title         text not null check (length(btrim(title)) > 0),
    description   text not null check (length(btrim(description)) > 0),
    sdg           int  not null check (sdg between 1 and 17),
    interest_ids  bigint[] not null default '{}',                     -- the interests it was themed on
    tech_stack    jsonb not null default '[]' check (jsonb_typeof(tech_stack) = 'array'),
    skill_ids     text[] not null default '{}',                       -- the roadmap skills it uses
    rubric        jsonb not null check (jsonb_typeof(rubric) = 'array'),
    -- open: nothing judged yet; judging: a submission is being judged now; judged: result holds the latest score
    status        text not null default 'open' check (status in ('open', 'judging', 'judged')),
    repo_url      text check (repo_url ~ '^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'),
    result        jsonb check (jsonb_typeof(result) = 'array'),
    score         numeric check (score between 0 and 100),
    summary       text,
    files_read    text[] not null default '{}',                       -- the repo files the judge was shown
    attempts      int  not null default 0 check (attempts >= 0),
    model         text,                                               -- the LLM that wrote it
    submitted_at  timestamptz,
    judged_at     timestamptz,
    created_at    timestamptz not null default now(),
    unique (roadmap_id, sections)
);

create index roadmap_challenge_roadmap_idx on public.roadmap_challenge (roadmap_id);

-- Personal, like roadmap: RLS on and no policies, so only the backend's service role reads or writes.
alter table public.roadmap_challenge enable row level security;
