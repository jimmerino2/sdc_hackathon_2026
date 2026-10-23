-- The UN Sustainable Development Goals each role's work serves, in the same shape as interests.sdg (0013): a jsonb
-- array of {"sdg": <1-17>, "value": <0-1>}, up to 3 goals per role, the values of one role adding up to 1.
-- The job matching step compares these with the goals behind a learner's interests, and the role page uses them to
-- explain why a role was suggested. load_supabase.py upserts only the CSV's columns, so reloading onet_roles keeps
-- these values.

alter table public.onet_roles
    add column sdg jsonb not null default '[]' check (jsonb_typeof(sdg) = 'array');

update public.onet_roles as r
set sdg = v.sdg
from (values
    ('11-2021.00', '[{"sdg": 8, "value": 0.5}, {"sdg": 12, "value": 0.3}, {"sdg": 9, "value": 0.2}]'::jsonb),  -- Marketing Managers
    ('13-1071.00', '[{"sdg": 8, "value": 0.5}, {"sdg": 10, "value": 0.3}, {"sdg": 5, "value": 0.2}]'::jsonb),  -- Human Resources Specialists
    ('13-1081.00', '[{"sdg": 9, "value": 0.4}, {"sdg": 12, "value": 0.35}, {"sdg": 13, "value": 0.25}]'::jsonb),  -- Logisticians
    ('13-1082.00', '[{"sdg": 8, "value": 0.4}, {"sdg": 9, "value": 0.35}, {"sdg": 17, "value": 0.25}]'::jsonb),  -- Project Management Specialists
    ('13-1161.00', '[{"sdg": 8, "value": 0.45}, {"sdg": 12, "value": 0.35}, {"sdg": 9, "value": 0.2}]'::jsonb),  -- Market Research Analysts and Marketing Specialists
    ('13-2011.00', '[{"sdg": 16, "value": 0.4}, {"sdg": 8, "value": 0.35}, {"sdg": 1, "value": 0.25}]'::jsonb),  -- Accountants and Auditors
    ('13-2053.00', '[{"sdg": 1, "value": 0.4}, {"sdg": 8, "value": 0.35}, {"sdg": 3, "value": 0.25}]'::jsonb),  -- Insurance Underwriters
    ('13-2072.00', '[{"sdg": 1, "value": 0.45}, {"sdg": 8, "value": 0.35}, {"sdg": 10, "value": 0.2}]'::jsonb),  -- Loan Officers
    ('15-1211.00', '[{"sdg": 9, "value": 0.5}, {"sdg": 8, "value": 0.3}, {"sdg": 17, "value": 0.2}]'::jsonb),  -- Computer Systems Analysts
    ('15-1212.00', '[{"sdg": 16, "value": 0.5}, {"sdg": 9, "value": 0.3}, {"sdg": 8, "value": 0.2}]'::jsonb),  -- Information Security Analysts
    ('15-1232.00', '[{"sdg": 4, "value": 0.4}, {"sdg": 9, "value": 0.35}, {"sdg": 10, "value": 0.25}]'::jsonb),  -- Computer User Support Specialists
    ('15-1252.00', '[{"sdg": 9, "value": 0.5}, {"sdg": 4, "value": 0.3}, {"sdg": 8, "value": 0.2}]'::jsonb),  -- Software Developers
    ('15-1255.00', '[{"sdg": 9, "value": 0.4}, {"sdg": 10, "value": 0.35}, {"sdg": 4, "value": 0.25}]'::jsonb),  -- Web and Digital Interface Designers
    ('15-2031.00', '[{"sdg": 9, "value": 0.4}, {"sdg": 12, "value": 0.35}, {"sdg": 13, "value": 0.25}]'::jsonb),  -- Operations Research Analysts
    ('15-2051.00', '[{"sdg": 9, "value": 0.4}, {"sdg": 3, "value": 0.35}, {"sdg": 13, "value": 0.25}]'::jsonb),  -- Data Scientists
    ('15-2051.01', '[{"sdg": 8, "value": 0.45}, {"sdg": 9, "value": 0.3}, {"sdg": 12, "value": 0.25}]'::jsonb),  -- Business Intelligence Analysts
    ('17-2071.00', '[{"sdg": 7, "value": 0.5}, {"sdg": 9, "value": 0.3}, {"sdg": 11, "value": 0.2}]'::jsonb),  -- Electrical Engineers
    ('17-2081.00', '[{"sdg": 6, "value": 0.4}, {"sdg": 13, "value": 0.35}, {"sdg": 15, "value": 0.25}]'::jsonb),  -- Environmental Engineers
    ('17-2112.00', '[{"sdg": 9, "value": 0.4}, {"sdg": 12, "value": 0.35}, {"sdg": 8, "value": 0.25}]'::jsonb),  -- Industrial Engineers
    ('19-2041.00', '[{"sdg": 13, "value": 0.4}, {"sdg": 15, "value": 0.35}, {"sdg": 14, "value": 0.25}]'::jsonb),  -- Environmental Scientists and Specialists, Including Health
    ('21-1093.00', '[{"sdg": 1, "value": 0.4}, {"sdg": 10, "value": 0.35}, {"sdg": 3, "value": 0.25}]'::jsonb),  -- Social and Human Service Assistants
    ('23-2011.00', '[{"sdg": 16, "value": 0.5}, {"sdg": 10, "value": 0.3}, {"sdg": 1, "value": 0.2}]'::jsonb),  -- Paralegals and Legal Assistants
    ('25-2011.00', '[{"sdg": 4, "value": 0.6}, {"sdg": 10, "value": 0.25}, {"sdg": 3, "value": 0.15}]'::jsonb),  -- Preschool Teachers, Except Special Education
    ('25-2021.00', '[{"sdg": 4, "value": 0.55}, {"sdg": 10, "value": 0.25}, {"sdg": 5, "value": 0.2}]'::jsonb),  -- Elementary School Teachers, Except Special Education
    ('27-3042.00', '[{"sdg": 4, "value": 0.4}, {"sdg": 9, "value": 0.35}, {"sdg": 17, "value": 0.25}]'::jsonb),  -- Technical Writers
    ('27-3091.00', '[{"sdg": 10, "value": 0.4}, {"sdg": 16, "value": 0.35}, {"sdg": 4, "value": 0.25}]'::jsonb),  -- Interpreters and Translators
    ('29-1123.00', '[{"sdg": 3, "value": 0.65}, {"sdg": 10, "value": 0.2}, {"sdg": 8, "value": 0.15}]'::jsonb),  -- Physical Therapists
    ('29-1141.00', '[{"sdg": 3, "value": 0.7}, {"sdg": 10, "value": 0.2}, {"sdg": 5, "value": 0.1}]'::jsonb),  -- Registered Nurses
    ('29-2052.00', '[{"sdg": 3, "value": 0.65}, {"sdg": 9, "value": 0.2}, {"sdg": 10, "value": 0.15}]'::jsonb),  -- Pharmacy Technicians
    ('29-9021.00', '[{"sdg": 3, "value": 0.5}, {"sdg": 9, "value": 0.3}, {"sdg": 16, "value": 0.2}]'::jsonb),  -- Health Information Technologists and Medical Registrars
    ('31-1122.00', '[{"sdg": 3, "value": 0.5}, {"sdg": 10, "value": 0.3}, {"sdg": 1, "value": 0.2}]'::jsonb),  -- Personal Care Aides
    ('33-9032.00', '[{"sdg": 16, "value": 0.6}, {"sdg": 11, "value": 0.4}]'::jsonb),  -- Security Guards
    ('35-2014.00', '[{"sdg": 2, "value": 0.5}, {"sdg": 3, "value": 0.3}, {"sdg": 8, "value": 0.2}]'::jsonb),  -- Cooks, Restaurant
    ('41-2031.00', '[{"sdg": 8, "value": 0.5}, {"sdg": 12, "value": 0.3}, {"sdg": 1, "value": 0.2}]'::jsonb),  -- Retail Salespersons
    ('43-3031.00', '[{"sdg": 8, "value": 0.5}, {"sdg": 16, "value": 0.3}, {"sdg": 1, "value": 0.2}]'::jsonb),  -- Bookkeeping, Accounting, and Auditing Clerks
    ('43-3071.00', '[{"sdg": 8, "value": 0.45}, {"sdg": 1, "value": 0.35}, {"sdg": 10, "value": 0.2}]'::jsonb),  -- Tellers
    ('43-4051.00', '[{"sdg": 8, "value": 0.5}, {"sdg": 12, "value": 0.3}, {"sdg": 9, "value": 0.2}]'::jsonb),  -- Customer Service Representatives
    ('43-6014.00', '[{"sdg": 8, "value": 0.6}, {"sdg": 16, "value": 0.25}, {"sdg": 5, "value": 0.15}]'::jsonb),  -- Secretaries and Administrative Assistants, Except Legal, Medical, and Executive
    ('43-9021.00', '[{"sdg": 8, "value": 0.6}, {"sdg": 9, "value": 0.4}]'::jsonb),  -- Data Entry Keyers
    ('47-2111.00', '[{"sdg": 7, "value": 0.45}, {"sdg": 9, "value": 0.3}, {"sdg": 11, "value": 0.25}]'::jsonb),  -- Electricians
    ('47-2231.00', '[{"sdg": 7, "value": 0.55}, {"sdg": 13, "value": 0.3}, {"sdg": 8, "value": 0.15}]'::jsonb),  -- Solar Photovoltaic Installers
    ('49-9071.00', '[{"sdg": 9, "value": 0.4}, {"sdg": 11, "value": 0.35}, {"sdg": 12, "value": 0.25}]'::jsonb),  -- Maintenance and Repair Workers, General
    ('49-9081.00', '[{"sdg": 7, "value": 0.5}, {"sdg": 13, "value": 0.35}, {"sdg": 8, "value": 0.15}]'::jsonb),  -- Wind Turbine Service Technicians
    ('51-2022.00', '[{"sdg": 9, "value": 0.5}, {"sdg": 8, "value": 0.3}, {"sdg": 12, "value": 0.2}]'::jsonb),  -- Electrical and Electronic Equipment Assemblers
    ('53-3032.00', '[{"sdg": 9, "value": 0.4}, {"sdg": 8, "value": 0.35}, {"sdg": 2, "value": 0.25}]'::jsonb),  -- Heavy and Tractor-Trailer Truck Drivers
    ('53-7062.00', '[{"sdg": 8, "value": 0.5}, {"sdg": 9, "value": 0.3}, {"sdg": 12, "value": 0.2}]'::jsonb)   -- Laborers and Freight, Stock, and Material Movers, Hand
) as v(onet_code, sdg)
where r.onet_code = v.onet_code;

-- Every role must now have 1 to 3 goals (1-17), each at most once, with values adding up to 1.
do $$
declare
    bad text;
begin
    select string_agg(r.onet_code, ', ') into bad
    from public.onet_roles r
    left join lateral (
        select count(*) as n,
               count(distinct (e ->> 'sdg')::int) as distinct_sdgs,
               min((e ->> 'sdg')::int) as lowest,
               max((e ->> 'sdg')::int) as highest,
               sum((e ->> 'value')::numeric) as total
        from jsonb_array_elements(r.sdg) e
    ) s on true
    where s.n not between 1 and 3 or s.n <> s.distinct_sdgs or s.lowest < 1 or s.highest > 17 or s.total <> 1;
    if bad is not null then
        raise exception 'roles with missing or invalid sdg weights: %', bad;
    end if;
end $$;
