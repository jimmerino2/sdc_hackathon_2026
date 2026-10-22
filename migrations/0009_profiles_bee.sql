-- The learner's companion bee. Everyone starts with Libbee and can switch to one of the others.
alter table public.profiles
    add column bee text not null default 'Libbee'
        check (bee in ('Libbee', 'Phoebee', 'Tobee', 'Barnabee'));
