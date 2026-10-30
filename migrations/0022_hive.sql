-- Protect the Hive: the boss fight where stingers are spent.
--
-- hive_fight is a lobby fighting Robbee: HP 100 -> 0 in 20-point stings, then a fresh Robbee at 100 in the SAME lobby
-- (kills counts the rounds), so a party stays together. A profile is in exactly one lobby (hive_member.profile_id is the
-- key), created on first visit; joining another's lobby (through a friend's invite) replaces it, and an empty lobby is
-- deleted. A lobby holds at most 4 members.
--
-- Spending a stinger (hive_sting): the oldest unspent stinger_award is marked spent, Robbee loses `damage` HP and the
-- stinger's owner gets `pollen`. On the killing blow, every member who stung this round (hive_member.stings > 0) and is
-- still in the lobby gets `kill_pollen`; every member gets a hive_reward row (pollen 0 for those who didn't sting) so
-- each sees the "Hive protected" popup once, with a snapshot of the party. Everything runs in SQL functions so two
-- members stinging at once can't lose an update; the amounts are passed in by the backend (app/hive/service.py).
--
-- hive_event is the "Recent hits" feed: stings, joins, leaves and kills per lobby, plus a learner's own 'twist' (Robbee
-- rewriting a challenge brief), which has no lobby. Service role only, like the other personal tables.

create table public.hive_fight (
    fight_id    uuid primary key default gen_random_uuid(),
    boss        text not null default 'robbee',
    hp          integer not null default 100 check (hp between 0 and 100),
    kills       integer not null default 0 check (kills >= 0),
    created_at  timestamptz not null default now()
);

create table public.hive_member (
    profile_id  uuid primary key references public.profiles (profile_id) on delete cascade,
    fight_id    uuid not null references public.hive_fight (fight_id) on delete cascade,
    joined_at   timestamptz not null default now(),
    stings      integer not null default 0 check (stings >= 0)   -- stingers spent this round; reset on a kill or a join
);

create index hive_member_fight_idx on public.hive_member (fight_id);

create table public.hive_invite (
    invite_id   uuid primary key default gen_random_uuid(),
    fight_id    uuid not null references public.hive_fight (fight_id) on delete cascade,
    from_id     uuid not null references public.profiles (profile_id) on delete cascade,
    to_id       uuid not null references public.profiles (profile_id) on delete cascade,
    created_at  timestamptz not null default now(),
    unique (fight_id, to_id)
);

create index hive_invite_to_idx on public.hive_invite (to_id);

create table public.hive_event (
    event_id      uuid primary key default gen_random_uuid(),
    fight_id      uuid references public.hive_fight (fight_id) on delete cascade,
    profile_id    uuid not null references public.profiles (profile_id) on delete cascade,
    kind          text not null check (kind in ('sting', 'twist', 'defeat', 'join', 'leave')),
    challenge_id  uuid references public.roadmap_challenge (challenge_id) on delete set null,
    pollen        integer not null default 0,
    created_at    timestamptz not null default now()
);

create index hive_event_fight_idx on public.hive_event (fight_id, created_at desc);
create index hive_event_profile_idx on public.hive_event (profile_id, created_at desc);

create table public.hive_reward (
    reward_id   uuid primary key default gen_random_uuid(),
    profile_id  uuid not null references public.profiles (profile_id) on delete cascade,
    fight_id    uuid references public.hive_fight (fight_id) on delete set null,
    round       integer not null,
    pollen      integer not null default 0,                       -- 0 when they were in the party but didn't sting
    party       jsonb not null,                                   -- [{"profile_id", "name", "bee", "stings"}] at the kill
    seen        boolean not null default false,
    created_at  timestamptz not null default now()
);

create index hive_reward_unseen_idx on public.hive_reward (profile_id, created_at) where not seen;

-- A stinger is spent by stinging; unspent ones are the learner's available stingers.
alter table public.stinger_award
    add column spent_at timestamptz,
    add column spent_fight_id uuid references public.hive_fight (fight_id) on delete set null;

alter table public.hive_fight  enable row level security;
alter table public.hive_member enable row level security;
alter table public.hive_invite enable row level security;
alter table public.hive_event  enable row level security;
alter table public.hive_reward enable row level security;

-- The profile's lobby, created (alone, Robbee at 100) the first time they need one.
create function public.hive_ensure(p_profile uuid) returns uuid
language plpgsql as $$
declare
    v_fight uuid;
begin
    perform pg_advisory_xact_lock(hashtextextended(p_profile::text, 0));
    select fight_id into v_fight from public.hive_member where profile_id = p_profile;
    if v_fight is null then
        insert into public.hive_fight default values returning fight_id into v_fight;
        insert into public.hive_member (profile_id, fight_id) values (p_profile, v_fight);
    end if;
    return v_fight;
end;
$$;

-- Spend a stinger on Robbee. Raises 'no_stinger' if the profile has none. Returns
-- {"defeated": bool, "pollen": <paid for this sting>, "kill_pollen": <paid to this profile for the kill, else 0>}.
create function public.hive_sting(p_profile uuid, p_damage integer, p_pollen integer, p_kill_pollen integer) returns jsonb
language plpgsql as $$
declare
    v_fight     uuid;
    v_hp        integer;
    v_kills     integer;
    v_challenge uuid;
    v_stage     smallint;
    v_party     jsonb;
    v_mine      integer := 0;
begin
    v_fight := public.hive_ensure(p_profile);
    -- Locking the lobby serialises everyone stinging in it.
    select hp, kills into v_hp, v_kills from public.hive_fight where fight_id = v_fight for update;

    select challenge_id, stage into v_challenge, v_stage from public.stinger_award
     where profile_id = p_profile and spent_at is null
     order by awarded_at, stage limit 1 for update skip locked;
    if not found then
        raise exception 'no_stinger';
    end if;

    update public.stinger_award set spent_at = now(), spent_fight_id = v_fight
     where challenge_id = v_challenge and stage = v_stage;
    update public.profiles set total_pollen = total_pollen + p_pollen where profile_id = p_profile;
    update public.hive_member set stings = stings + 1 where profile_id = p_profile;
    insert into public.hive_event (fight_id, profile_id, kind, challenge_id, pollen)
        values (v_fight, p_profile, 'sting', v_challenge, p_pollen);

    v_hp := greatest(v_hp - p_damage, 0);
    if v_hp > 0 then
        update public.hive_fight set hp = v_hp where fight_id = v_fight;
        return jsonb_build_object('defeated', false, 'pollen', p_pollen, 'kill_pollen', 0);
    end if;

    -- The kill: snapshot the party, pay those who stung this round, let everyone see the popup, then a fresh Robbee.
    select jsonb_agg(jsonb_build_object('profile_id', m.profile_id, 'name', pr.name, 'bee', pr.bee, 'stings', m.stings) order by m.joined_at)
      into v_party
      from public.hive_member m join public.profiles pr on pr.profile_id = m.profile_id
     where m.fight_id = v_fight;

    insert into public.hive_reward (profile_id, fight_id, round, pollen, party)
        select m.profile_id, v_fight, v_kills + 1, case when m.stings > 0 then p_kill_pollen else 0 end, v_party
          from public.hive_member m where m.fight_id = v_fight;
    update public.profiles set total_pollen = total_pollen + p_kill_pollen
     where profile_id in (select profile_id from public.hive_member where fight_id = v_fight and stings > 0);
    select stings into v_mine from public.hive_member where profile_id = p_profile;

    insert into public.hive_event (fight_id, profile_id, kind) values (v_fight, p_profile, 'defeat');
    update public.hive_member set stings = 0 where fight_id = v_fight;
    update public.hive_fight set hp = 100, kills = kills + 1 where fight_id = v_fight;
    return jsonb_build_object('defeated', true, 'pollen', p_pollen, 'kill_pollen', case when v_mine > 0 then p_kill_pollen else 0 end);
end;
$$;

-- Accept an invite: move into that lobby, leaving (and, if it empties, deleting) the current one. Raises 'no_invite'
-- if it isn't this profile's or its lobby is gone, 'party_full' if the lobby already has p_max members.
create function public.hive_join(p_profile uuid, p_invite uuid, p_max integer) returns uuid
language plpgsql as $$
declare
    v_fight uuid;
    v_old   uuid;
    v_count integer;
begin
    perform pg_advisory_xact_lock(hashtextextended(p_profile::text, 0));
    select fight_id into v_fight from public.hive_invite where invite_id = p_invite and to_id = p_profile;
    if v_fight is null then
        raise exception 'no_invite';
    end if;
    perform 1 from public.hive_fight where fight_id = v_fight for update;   -- serialise joins into one lobby
    select fight_id into v_old from public.hive_member where profile_id = p_profile;
    if v_old = v_fight then
        delete from public.hive_invite where invite_id = p_invite;
        return v_fight;
    end if;
    select count(*) into v_count from public.hive_member where fight_id = v_fight;
    if v_count = 0 then
        raise exception 'no_invite';
    elsif v_count >= p_max then
        raise exception 'party_full';
    end if;

    if v_old is null then
        insert into public.hive_member (profile_id, fight_id) values (p_profile, v_fight);
    else
        update public.hive_member set fight_id = v_fight, joined_at = now(), stings = 0 where profile_id = p_profile;
    end if;
    delete from public.hive_invite where invite_id = p_invite;
    insert into public.hive_event (fight_id, profile_id, kind) values (v_fight, p_profile, 'join');
    if v_old is not null then
        if exists (select 1 from public.hive_member where fight_id = v_old) then
            insert into public.hive_event (fight_id, profile_id, kind) values (v_old, p_profile, 'leave');
        else
            delete from public.hive_fight where fight_id = v_old;
        end if;
    end if;
    return v_fight;
end;
$$;

-- Leave the party for a fresh solo lobby (Robbee at 100). Already alone: nothing changes.
create function public.hive_leave(p_profile uuid) returns uuid
language plpgsql as $$
declare
    v_old uuid;
    v_new uuid;
begin
    v_old := public.hive_ensure(p_profile);
    if (select count(*) from public.hive_member where fight_id = v_old) <= 1 then
        return v_old;
    end if;
    insert into public.hive_fight default values returning fight_id into v_new;
    update public.hive_member set fight_id = v_new, joined_at = now(), stings = 0 where profile_id = p_profile;
    insert into public.hive_event (fight_id, profile_id, kind) values (v_old, p_profile, 'leave');
    return v_new;
end;
$$;
