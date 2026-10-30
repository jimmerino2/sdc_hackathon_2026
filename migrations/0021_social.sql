-- Social: pollen and friends.
--
-- profiles.total_pollen is the learner's pollen, 0 to start. It is earned (500 per stinger, boss kills later) and
-- ranks the leaderboard, which shows the learner and their accepted friends, highest first. Changed only through
-- add_pollen(), so two awards at once can't overwrite each other.
--
-- A friend request names an email, not a profile: names are not unique, and the person may not have signed up yet.
-- social_friendship.addressee_email is lower-cased; the request reaches whichever profile is synced with that email
-- (now or later). Pending until accepted by the addressee; either side can remove it, or the friendship, at any time.
-- Friends are the accepted rows with the learner on either side. Service role only, like the other personal tables.

alter table public.profiles
    add column total_pollen integer not null default 0 check (total_pollen >= 0);

create function public.add_pollen(p_profile_id uuid, p_amount integer) returns integer
language sql as $$
    update public.profiles set total_pollen = greatest(total_pollen + p_amount, 0)
    where profile_id = p_profile_id
    returning total_pollen;
$$;

create table public.social_friendship (
    friendship_id    uuid primary key default gen_random_uuid(),
    requester_id     uuid not null references public.profiles (profile_id) on delete cascade,
    addressee_email  text not null check (addressee_email = lower(btrim(addressee_email)) and length(addressee_email) > 2),
    status           text not null default 'pending' check (status in ('pending', 'accepted')),
    created_at       timestamptz not null default now(),
    accepted_at      timestamptz,
    unique (requester_id, addressee_email)
);

create index social_friendship_addressee_idx on public.social_friendship (addressee_email);

alter table public.social_friendship enable row level security;
