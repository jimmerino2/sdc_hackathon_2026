import { skillLabel } from './skills';

/**
 * Skill keywords found in the resume text, so they can be highlighted on the page while the API scores the file.
 * Each entry is [display name, aliases]. Keep it in step with the taxonomy the backend matches against
 * (O*NET technology skills) so the highlights and the API result agree.
 */
const DICT: [string, string[]][] = [
  ['JavaScript', ['JavaScript', 'JS', 'ECMAScript']], ['TypeScript', ['TypeScript']], ['Python', ['Python', 'PySpark']], ['Java', ['Java']],
  ['PHP', ['PHP']], ['C#', ['C#']], ['C++', ['C++']], ['Kotlin', ['Kotlin']], ['Swift', ['Swift']], ['SQL', ['SQL', 'T-SQL', 'PL/SQL']],
  ['HTML', ['HTML', 'HTML5']], ['CSS', ['CSS', 'CSS3', 'SCSS', 'Sass']], ['Bash', ['Bash', 'Shell scripting']],
  ['React', ['React', 'React.js', 'ReactJS']], ['React Native', ['React Native']], ['Next.js', ['Next.js', 'NextJS']], ['Vue', ['Vue', 'Vue.js']], ['Angular', ['Angular']],
  ['Node.js', ['Node.js', 'NodeJS', 'Node']], ['Express.js', ['Express.js', 'ExpressJS']], ['NestJS', ['NestJS', 'Nest.js']], ['Laravel', ['Laravel']], ['Django', ['Django']], ['Flask', ['Flask']],
  ['Spring Boot', ['Spring Boot']], ['.NET', ['.NET', 'ASP.NET']], ['Tailwind CSS', ['Tailwind CSS', 'Tailwind']], ['Redux', ['Redux']],
  ['MySQL', ['MySQL']], ['PostgreSQL', ['PostgreSQL', 'Postgres']], ['MongoDB', ['MongoDB']], ['Redis', ['Redis']], ['DynamoDB', ['DynamoDB', 'Amazon DynamoDB']],
  ['Redshift', ['Redshift', 'Amazon Redshift']], ['Snowflake', ['Snowflake']], ['Elasticsearch', ['Elasticsearch']], ['Kafka', ['Kafka']], ['Spark', ['Apache Spark']], ['Airflow', ['Airflow']],
  ['AWS', ['AWS', 'Amazon Web Services']], ['Azure', ['Azure']], ['Google Cloud', ['Google Cloud', 'GCP']], ['Docker', ['Docker']], ['Kubernetes', ['Kubernetes', 'K8s']],
  ['Terraform', ['Terraform']], ['Jenkins', ['Jenkins']], ['GitHub Actions', ['GitHub Actions']], ['CI/CD', ['CI/CD']], ['Linux', ['Linux']], ['Git', ['Git']], ['GitHub', ['GitHub']], ['GitLab', ['GitLab']], ['Nginx', ['Nginx']],
  ['REST APIs', ['REST', 'RESTful', 'REST API', 'REST APIs', 'RESTful API']], ['GraphQL', ['GraphQL']], ['Microservices', ['Microservices']],
  ['Agile', ['Agile']], ['Scrum', ['Scrum']], ['Jest', ['Jest']], ['Cypress', ['Cypress']], ['Playwright', ['Playwright']], ['Figma', ['Figma']], ['Jira', ['Jira']],
  ['Machine Learning', ['Machine Learning']], ['ETL', ['ETL']], ['Power BI', ['Power BI']], ['Tableau', ['Tableau']], ['QuickSight', ['QuickSight']],
];

const ALIAS_TO = new Map<string, string>();
for (const [name, aliases] of DICT) for (const a of aliases) ALIAS_TO.set(a.toLowerCase(), name);

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');
/** Longest alias first, and boundaries so "Java" doesn't match in "JavaScript" nor "SQL" in "NoSQL". */
const MATCHER = new RegExp(
  `(?<![A-Za-z0-9+#.])(${[...ALIAS_TO.keys()].sort((a, b) => b.length - a.length).map(escapeRe).join('|')})(?![A-Za-z0-9+#])`,
  'gi',
);

export interface KeywordHit {
  /** Display name, e.g. "REST APIs". */
  key: string;
  start: number;
  end: number;
}

export function findKeywords(text: string): KeywordHit[] {
  return [...text.matchAll(MATCHER)].map((m) => ({ key: ALIAS_TO.get(m[1].toLowerCase())!, start: m.index!, end: m.index! + m[1].length }));
}

/** Taxonomy names the shared labels don't shorten. */
const EXTRA_LABELS: Record<string, string> = { 'Amazon Redshift': 'Redshift', 'Amazon DynamoDB': 'DynamoDB' };

/** What a person would write for an API skill name, so it can be matched against the highlights. */
export function displayName(apiName: string): string {
  if (EXTRA_LABELS[apiName]) return EXTRA_LABELS[apiName];
  const label = skillLabel(apiName);
  if (label !== apiName.replace(/ software$/, '')) return label;
  const acronym = apiName.match(/\b([A-Z]{2,5})\b(?: software)?$/);
  return acronym ? acronym[1] : label;
}
