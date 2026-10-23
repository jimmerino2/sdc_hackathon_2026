-- Why a role fits one of a learner's interests: a short sentence, written by the LLM the first time someone opens
-- that role's details with that interest picked, then kept here so it is written only once. One row per role, goal
-- and interest (the "Your interests" cards on the role page pair each SDG with the interests that point at it).
-- Nothing in it is personal, so one learner's sentence is reused for everyone with the same interest.

create table public.role_interest_reasons (
    onet_code   text    not null references public.onet_roles (onet_code) on delete cascade,
    sdg         int     not null check (sdg between 1 and 17),
    interest_id bigint  not null references public.interests (id) on delete cascade,
    reason      text    not null check (length(btrim(reason)) > 0),
    model       text,                                   -- the LLM that wrote it
    created_at  timestamptz not null default now(),
    primary key (onet_code, sdg, interest_id)
);

-- Written and read only by the backend (service role), like profiles: RLS on and no policies.
alter table public.role_interest_reasons enable row level security;
