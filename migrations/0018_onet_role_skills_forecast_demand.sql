-- Adds onet_role_skills.forecast_demand: the occupational-forecasting dataset's 6-month-ahead forecast share of
-- US job ads naming the skill (0-1), for this skill_name in this onet_code. Null where the skill isn't tracked
-- by that dataset, or the role isn't one of the occupations it covers. Like skill_group (migration 0012), this is
-- SQL-only: it isn't in data/processed/onet_role_skills.csv, so reloading that CSV (load_supabase.py upserts,
-- never deletes/overwrites columns it doesn't carry) leaves these values alone.
--
-- Matched the same way as migration 0017: a skill_name is matched to a tracked forecast skill by exact name
-- first, then (for the many O*NET names that spell a tracked skill differently, e.g. "Structured query language
-- SQL") by the forecasting pipeline's own curated_skills.csv patterns; left null on no match or an ambiguous one.
-- Only the roles the forecasting dataset covers have any matches: Software Developers (15-1252.00), Data
-- Scientists (15-2051.00), Data Analysts (15-2051.01). Several related O*NET names share one tracked skill and so
-- share one value (e.g. "Structured query language SQL", "Oracle PL/SQL" and "Transact-SQL" all read as "sql").
--
-- Used by the roadmap planner (src/backend/app/roadmap/planner.py) alongside importance when it chooses which
-- candidate skills to keep.

alter table public.onet_role_skills add column forecast_demand numeric;

update public.onet_role_skills as s
set forecast_demand = g.forecast_demand
from (values
    ('Amazon DynamoDB', 0.0058),
    ('Amazon Redshift', 0.0022),
    ('Amazon Web Services AWS CloudFormation', 0.2096),
    ('Amazon Web Services AWS software', 0.2096),
    ('Apache Airflow', 0.011),
    ('Apache Cassandra', 0.0022),
    ('Apache Hive', 0.0015),
    ('Apache Kafka', 0.0168),
    ('Apache Spark', 0.0073),
    ('Apple iOS', 0.0402),
    ('Bash', 0.0022),
    ('C', 0.0226),
    ('C#', 0.0226),
    ('C++', 0.0226),
    ('Cascading style sheets CSS', 0.0314),
    ('Django', 0.0446),
    ('Docker', 0.0665),
    ('Elasticsearch', 0.0168),
    ('Flask', 0.0073),
    ('Git', 0.0957),
    ('GitHub', 0.0957),
    ('GitLab', 0.0957),
    ('Go', 0.0913),
    ('Google Android', 0.0299),
    ('Google Angular', 0.0044),
    ('Google Cloud', 0.0584),
    ('Google Looker Analytics', 0.0029),
    ('Grafana Labs Grafana Cloud', 0.0723),
    ('GraphQL', 0.0519),
    ('Hugging Face', 0.0117),
    ('Hypertext markup language HTML', 0.0314),
    ('IBM SPSS Statistics', 0.0058),
    ('IBM Terraform', 0.073),
    ('JavaScript', 0.0489),
    ('JavaScript Object Notation JSON', 0.0489),
    ('Jenkins CI', 0.0592),
    ('Kotlin', 0.0219),
    ('Kubernetes', 0.1264),
    ('LangChain', 0.0146),
    ('Linux', 0.0292),
    ('Microsoft .NET Framework', 0.0161),
    ('Microsoft ASP.NET', 0.0161),
    ('Microsoft Azure software', 0.0263),
    ('Microsoft Excel', 0.0168),
    ('Microsoft Power BI', 0.0007),
    ('MongoDB', 0.0278),
    ('MySQL', 0.019),
    ('Node.js', 0.1103),
    ('OpenAI API', 0.0416),
    ('Oracle Java', 0.0446),
    ('Oracle Java 2 Platform Enterprise Edition J2EE', 0.0446),
    ('Oracle PL/SQL', 0.0329),
    ('Oracle SQL Developer', 0.0329),
    ('PHP', 0.0102),
    ('PostgreSQL', 0.2345),
    ('Prometheus', 0.0723),
    ('PyTorch', 0.0146),
    ('Python', 0.2885),
    ('R', 0.0007),
    ('RESTful API', 0.011),
    ('React', 0.3214),
    ('React Native', 0.0482),
    ('Red Hat Enterprise Linux', 0.0292),
    ('Redis', 0.0329),
    ('Ruby', 0.0212),
    ('Ruby on Rails', 0.0482),
    ('Rust', 0.0928),
    ('SQLite', 0.0022),
    ('Scala', 0.0226),
    ('Selenium', 0.019),
    ('Snowflake', 0.0124),
    ('Solidity', 0.0066),
    ('Spring Boot', 0.0037),
    ('Spring Framework', 0.0037),
    ('Structured query language SQL', 0.0329),
    ('Swift', 0.0146),
    ('Tableau', 0.0007),
    ('TensorFlow', 0.0015),
    ('The MathWorks MATLAB', 0.0),
    ('Transact-SQL', 0.0329),
    ('TypeScript', 0.3353),
    ('UNIX', 0.0292),
    ('UNIX Shell', 0.0292),
    ('Vue.js', 0.019)
) as g (skill_name, forecast_demand)
where s.onet_code = '15-1252.00' and s.skill_name = g.skill_name;

update public.onet_role_skills as s
set forecast_demand = g.forecast_demand
from (values
    ('Amazon Web Services AWS software', 0.0556),
    ('Apache Hadoop', 0.0),
    ('Apache Kafka', 0.0),
    ('Apache Spark', 0.0),
    ('C++', 0.0),
    ('Git', 0.0556),
    ('GitHub', 0.0556),
    ('IBM SPSS Statistics', 0.0278),
    ('JavaScript', 0.0278),
    ('JavaScript Object Notation JSON', 0.0278),
    ('Microsoft Azure software', 0.0556),
    ('Microsoft Excel', 0.0278),
    ('Microsoft Power BI', 0.0278),
    ('NumPy', 0.0556),
    ('Oracle Java', 0.1111),
    ('PostgreSQL', 0.0),
    ('PyTorch', 0.0278),
    ('Python', 0.1111),
    ('R', 0.0278),
    ('SAS', 0.0278),
    ('Scala', 0.0),
    ('Scikit-learn', 0.0556),
    ('Snowflake', 0.0278),
    ('Structured query language SQL', 0.1111),
    ('Tableau', 0.0278),
    ('TensorFlow', 0.0278),
    ('pandas', 0.0556)
) as g (skill_name, forecast_demand)
where s.onet_code = '15-2051.00' and s.skill_name = g.skill_name;

update public.onet_role_skills as s
set forecast_demand = g.forecast_demand
from (values
    ('Amazon Redshift', 0.1053),
    ('Amazon Web Services AWS software', 0.0526),
    ('Apache Kafka', 0.0),
    ('C', 0.0526),
    ('Go', 0.0),
    ('Google Looker Analytics', 0.1053),
    ('IBM SPSS Statistics', 0.1053),
    ('JavaScript', 0.1053),
    ('JavaScript Object Notation JSON', 0.1053),
    ('Linux', 0.1053),
    ('Microsoft .NET Framework', 0.0526),
    ('Microsoft ASP.NET', 0.0526),
    ('Microsoft Azure software', 0.0526),
    ('Microsoft Excel', 0.0526),
    ('Microsoft Power BI', 0.0526),
    ('Oracle Java', 0.1579),
    ('Oracle PL/SQL', 0.3158),
    ('Oracle SQL Developer', 0.3158),
    ('PostgreSQL', 0.1053),
    ('Python', 0.2632),
    ('React', 0.0526),
    ('Red Hat Enterprise Linux', 0.1053),
    ('Snowflake', 0.1053),
    ('Structured query language SQL', 0.3158),
    ('Swift', 0.0526),
    ('Tableau', 0.0526),
    ('Transact-SQL', 0.3158),
    ('TypeScript', 0.1579),
    ('UNIX', 0.1053),
    ('UNIX Shell', 0.1053),
    ('pandas', 0.1053)
) as g (skill_name, forecast_demand)
where s.onet_code = '15-2051.01' and s.skill_name = g.skill_name;
