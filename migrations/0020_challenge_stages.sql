-- Challenges in two stages, and stingers. Replaces 0016's roadmap_challenge (its rows are dropped: a full wipe follows).
--
-- A challenge belongs to a profile and a tech role (onet_code). A profile may have any number per role. It is tied to
-- a roadmap only optionally: building a tech-role roadmap writes one challenge linked to it, and more can be started
-- from the Challenges page (POST /roadmap/challenges) with no roadmap at all. Deleting the roadmap keeps the
-- challenge, its progress and its stingers; only the link is cleared.
--
-- Stage 1 draws on the roadmap's sections 1-2 when linked, otherwise on the role's foundational O*NET skills. It is
-- open from the start, whatever the roadmap progress. A judged score of 85+ passes the stage and awards a stinger.
-- Passing stage 1 lets Robbee rewrite the project (POST /roadmap/challenge/{id}/advance): the LLM writes a harder
-- stage 2 from the later sections (or the role's other skills), and the current-stage columns are overwritten with
-- it, stage 1's final result moving into history. Passing stage 2 awards a second stinger and completes the
-- challenge. A completed challenge may be resubmitted to improve its score; it stays complete and pays no more
-- stingers.
--
-- repo_url is the challenge's own repo: it is kept when the challenge moves to stage 2 (both stages are built in the
-- same repo) and can be changed by submitting a different one.
--
-- The brief and result columns always describe the current stage, in the shapes 0016 documents:
-- tech_stack [{"area", "skills": [<O*NET skill_name>]}], rubric [{"key", "criterion", "description", "weight"}] with
-- weights adding up to 100, result [{"key", "score", "why", "improve"}]. history holds each earlier stage as
-- {"stage", "title", "repo_url", "score", "summary", "judged_at"}.

drop table if exists public.stinger_award;
drop table if exists public.roadmap_challenge;

create table public.roadmap_challenge (
    challenge_id  uuid primary key default gen_random_uuid(),
    profile_id    uuid not null references public.profiles (profile_id) on delete cascade,
    onet_code     text not null references public.onet_roles (onet_code),
    roadmap_id    uuid references public.roadmap (roadmap_id) on delete set null,  -- optional
    stage         smallint not null default 1 check (stage in (1, 2)),
    sections      int[] not null default '{}',                        -- the roadmap sections the current stage draws on; empty without a roadmap
    title         text not null check (length(btrim(title)) > 0),
    description   text not null check (length(btrim(description)) > 0),
    twist         text,                                               -- stage 2: what Robbee changed, one line
    sdg           int  not null check (sdg between 1 and 17),
    interest_ids  bigint[] not null default '{}',
    tech_stack    jsonb not null default '[]' check (jsonb_typeof(tech_stack) = 'array'),
    skill_ids     text[] not null default '{}',
    rubric        jsonb not null check (jsonb_typeof(rubric) = 'array'),
    -- open: not yet passed; judging: a submission is being judged; passed: the current stage scored 85+;
    -- advancing: stage 2 is being written after a stage 1 pass
    status        text not null default 'open' check (status in ('open', 'judging', 'passed', 'advancing')),
    repo_url      text check (repo_url ~ '^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'),
    result        jsonb check (jsonb_typeof(result) = 'array'),
    score         numeric check (score between 0 and 100),
    summary       text,
    files_read    text[] not null default '{}',
    attempts      int  not null default 0 check (attempts >= 0),     -- submissions at the current stage
    history       jsonb not null default '[]' check (jsonb_typeof(history) = 'array'),
    model         text,
    busy_since    timestamptz,                                        -- when judging/advancing started; stale ones may be retaken
    judged_at     timestamptz,
    completed_at  timestamptz,                                        -- stage 2 passed
    created_at    timestamptz not null default now()
);

create index roadmap_challenge_profile_idx on public.roadmap_challenge (profile_id, onet_code);
create index roadmap_challenge_roadmap_idx on public.roadmap_challenge (roadmap_id);

alter table public.roadmap_challenge enable row level security;

-- Stingers: one per passed stage, so a learner's total is their row count.
create table public.stinger_award (
    challenge_id  uuid not null references public.roadmap_challenge (challenge_id) on delete cascade,
    stage         smallint not null check (stage in (1, 2)),
    profile_id    uuid not null references public.profiles (profile_id) on delete cascade,
    score         numeric not null check (score between 0 and 100),
    awarded_at    timestamptz not null default now(),
    primary key (challenge_id, stage)
);

create index stinger_award_profile_idx on public.stinger_award (profile_id);

alter table public.stinger_award enable row level security;
