-- Everyday interests a learner can pick (cooking, sports, design...), each tied to the UN Sustainable Development
-- Goals it serves behind the scenes, and the
-- many-to-many link between profiles and interests. Replaces profiles.concerns (the free-text "worries"),
-- which is dropped here.
--
-- interests.sdg is a jsonb array of {"sdg": <1-17>, "value": <0-1>}: up to 3 goals per interest, and the values
-- of one interest add up to 1 (checked at the end of this file). A bigger value means the interest serves
-- that goal more.

create table public.interests (
    id          bigint generated always as identity primary key,
    interest    text not null unique check (length(btrim(interest)) > 0),
    description text not null check (length(btrim(description)) > 0),
    icon        text not null default 'sparkles' check (icon ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),  -- a Lucide icon name, like onet_roles.icon
    sdg         jsonb not null default '[]' check (jsonb_typeof(sdg) = 'array')
);

-- Reference data: public read-only for the anon key, like the other reference tables. Only the service role writes.
alter table public.interests enable row level security;
create policy "public read" on public.interests for select to anon, authenticated using (true);

-- Which interests a profile picked. Deleting a profile or an interest removes its links.
create table public.profile_interests (
    profile_id  uuid   not null references public.profiles (profile_id) on delete cascade,
    interest_id bigint not null references public.interests (id) on delete cascade,
    primary key (profile_id, interest_id)
);

create index profile_interests_interest_idx on public.profile_interests (interest_id);

-- Private, like profiles: RLS on and no policies, so only the backend's service-role key can read or write.
alter table public.profile_interests enable row level security;

-- The free-text worries are replaced by interests.
alter table public.profiles drop column concerns;

insert into public.interests (interest, description, icon, sdg) values
    ('Cooking & Baking', 'Trying recipes, feeding people and finding out where food comes from.', 'chef-hat',
        '[{"sdg": 2, "value": 0.5}, {"sdg": 3, "value": 0.3}, {"sdg": 12, "value": 0.2}]'),
    ('Gardening & Farming', 'Growing plants and food, from a balcony herb pot to a working farm.', 'sprout',
        '[{"sdg": 2, "value": 0.45}, {"sdg": 15, "value": 0.35}, {"sdg": 13, "value": 0.2}]'),
    ('Sports & Fitness', 'Playing, training and keeping active, alone or in a team.', 'dumbbell',
        '[{"sdg": 3, "value": 0.6}, {"sdg": 10, "value": 0.25}, {"sdg": 5, "value": 0.15}]'),
    ('Music, Art & Performance', 'Making or enjoying music, drawing, theatre, film and other creative work.', 'music',
        '[{"sdg": 11, "value": 0.45}, {"sdg": 4, "value": 0.35}, {"sdg": 10, "value": 0.2}]'),
    ('Design & Making', 'Sketching, prototyping and building things people use, from posters to products.', 'pen-tool',
        '[{"sdg": 9, "value": 0.45}, {"sdg": 12, "value": 0.35}, {"sdg": 11, "value": 0.2}]'),
    ('Charity & Volunteering', 'Giving time or money to causes and helping people who are struggling.', 'hand-heart',
        '[{"sdg": 1, "value": 0.45}, {"sdg": 10, "value": 0.3}, {"sdg": 17, "value": 0.25}]'),
    ('Animals & Wildlife', 'Pets, rescue, zoos and protecting the animals we share the planet with.', 'paw-print',
        '[{"sdg": 15, "value": 0.5}, {"sdg": 14, "value": 0.3}, {"sdg": 13, "value": 0.2}]'),
    ('Gaming & Coding', 'Video games, apps and tinkering with code or gadgets.', 'gamepad-2',
        '[{"sdg": 9, "value": 0.5}, {"sdg": 4, "value": 0.3}, {"sdg": 8, "value": 0.2}]'),
    ('Teaching & Mentoring', 'Explaining things, tutoring and helping others learn.', 'graduation-cap',
        '[{"sdg": 4, "value": 0.6}, {"sdg": 10, "value": 0.25}, {"sdg": 8, "value": 0.15}]'),
    ('Fashion & Thrifting', 'Style, second-hand finds and clothes made to last.', 'shirt',
        '[{"sdg": 12, "value": 0.6}, {"sdg": 8, "value": 0.25}, {"sdg": 13, "value": 0.15}]'),
    ('Fixing & Building', 'Repairs, DIY and engineering projects, from bikes to buildings.', 'hammer',
        '[{"sdg": 9, "value": 0.45}, {"sdg": 11, "value": 0.3}, {"sdg": 12, "value": 0.25}]'),
    ('Mental Health & Wellness', 'Looking after your mind, talking things through and supporting friends.', 'heart-pulse',
        '[{"sdg": 3, "value": 0.65}, {"sdg": 10, "value": 0.2}, {"sdg": 4, "value": 0.15}]'),
    ('Nature & Outdoors', 'Hiking, beaches, recycling and spending time in the wild.', 'mountain',
        '[{"sdg": 13, "value": 0.4}, {"sdg": 15, "value": 0.35}, {"sdg": 14, "value": 0.25}]'),
    ('Money & Starting a Business', 'Side hustles, selling things, saving and building something of your own.', 'coins',
        '[{"sdg": 8, "value": 0.5}, {"sdg": 1, "value": 0.3}, {"sdg": 9, "value": 0.2}]'),
    ('Politics & Community Issues', 'Debating, following the news and standing up for fairness in your community.', 'landmark',
        '[{"sdg": 16, "value": 0.5}, {"sdg": 10, "value": 0.3}, {"sdg": 17, "value": 0.2}]');

-- Every seeded interest must have 1 to 3 goals (1-17), each at most once, with values adding up to 1.
do $$
declare
    bad text;
begin
    select string_agg(interest, ', ') into bad
    from (
        select i.interest
        from public.interests i
        cross join lateral (
            select count(*) as n,
                   count(distinct (e ->> 'sdg')::int) as distinct_sdgs,
                   min((e ->> 'sdg')::int) as lowest,
                   max((e ->> 'sdg')::int) as highest,
                   sum((e ->> 'value')::numeric) as total
            from jsonb_array_elements(i.sdg) e
        ) s
        where s.n not between 1 and 3 or s.n <> s.distinct_sdgs or s.lowest < 1 or s.highest > 17 or s.total <> 1
    ) x;
    if bad is not null then
        raise exception 'interests with invalid sdg weights: %', bad;
    end if;
end $$;
