-- Closes the gap between the occupational-forecasting dataset (src/backend/occupational, /occupations page) and
-- onet_role_skills: tools the forecasting pipeline tracks with real, recent job-ad evidence (last_share_3m > 0,
-- US, h=6) for Software Engineer (15-1252.00) and Data Analyst (15-2051.01), that O*NET's own technology-skills
-- list for that role doesn't name (checked against the curated_skills.csv patterns, not just exact text, so e.g.
-- "AWS" was correctly left out: it already matches "Amazon Web Services AWS software").
--
-- Scope: only named tools/languages/frameworks, not broader practice/competency entries the forecasting data also
-- tracks (e.g. "DevOps", "Compliance & auditing") and not its lower-confidence auto-discovered ("cand:") entries.
-- Data Scientist (15-2051.00)'s only candidate was one such competency entry, so it has no rows here.
--
-- importance follows the existing tech convention (STRUCTURE.md: 4.0 "In Demand", 3.5 "Hot Technology" tier,
-- O*NET doesn't rate these for this role, so this is a judgment call): 4.0 for the software_engineer skills at or
-- above 5% recent share (comparably prominent to the role's existing "In Demand" entries), 3.5 for the rest,
-- including every data_analyst skill (each on a single ad out of six recent, i.e. barely attested yet).
-- skill_group matches migration 0012's mapping where the skill maps onto an existing group; OpenAI API, LangChain
-- and Hugging Face fold into 'Data Science & ML', the closest existing bucket, rather than a new group of three.
-- level stays null, same as every other tech row (STRUCTURE.md: level is O*NET-rated and tech rows don't have one).

insert into public.onet_role_skills (onet_code, skill_id, skill_name, skill_type, importance, skill_group)
values
    ('15-1252.00', 'tech:rust',          'Rust',           'tech', 4.0, 'Programming Languages'),
    ('15-1252.00', 'tech:google-cloud',  'Google Cloud',   'tech', 4.0, 'Cloud & DevOps'),
    ('15-1252.00', 'tech:ruby-on-rails', 'Ruby on Rails',  'tech', 4.0, 'Backend Development'),
    ('15-1252.00', 'tech:react-native',  'React Native',   'tech', 4.0, 'Mobile Development'),
    ('15-1252.00', 'tech:cpp',           'C++',            'tech', 3.5, 'Programming Languages'),
    ('15-1252.00', 'tech:csharp',        'C#',             'tech', 3.5, 'Programming Languages'),
    ('15-1252.00', 'tech:openai-api',    'OpenAI API',     'tech', 3.5, 'Data Science & ML'),
    ('15-1252.00', 'tech:kotlin',        'Kotlin',         'tech', 3.5, 'Programming Languages'),
    ('15-1252.00', 'tech:langchain',     'LangChain',      'tech', 3.5, 'Data Science & ML'),
    ('15-1252.00', 'tech:solidity',      'Solidity',       'tech', 3.5, 'Programming Languages'),
    ('15-1252.00', 'tech:sqlite',        'SQLite',         'tech', 3.5, 'Databases & SQL'),
    ('15-1252.00', 'tech:flask',         'Flask',          'tech', 3.5, 'Backend Development'),
    ('15-1252.00', 'tech:hugging-face',  'Hugging Face',   'tech', 3.5, 'Data Science & ML'),
    ('15-2051.01', 'tech:pandas',        'pandas',         'tech', 3.5, 'Data Science & ML'),
    ('15-2051.01', 'tech:react',         'React',          'tech', 3.5, 'Web Development'),
    ('15-2051.01', 'tech:typescript',    'TypeScript',     'tech', 3.5, 'Web Development')
on conflict (onet_code, skill_id) do nothing;
