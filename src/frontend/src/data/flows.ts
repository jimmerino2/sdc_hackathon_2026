export type PersonaKey = 'a' | 'b' | 'c';
export type ScenarioKey = 'accelerates' | 'steady' | 'slows';
export type IconName = 'sparkles' | 'cpu' | 'shield' | 'code' | 'database' | 'cloud' | 'layers' | 'bug';

export interface Role {
  id: string;
  title: string;
  icon: IconName;
  match: number;
  haveCount: number;
  total: number;
  growth: string;
  blurb: string;
  have: string[];
  gap: string[];
}

export interface Persona {
  key: PersonaKey;
  label: string;
  userType: string;
  name: string;
  age: number;
  summary: string;
  quote: string;
  feels: string;
  needs: string;
  whoIndex: number;
  mascotWelcome: string;
  mindBubble: string;
  timeline: string;
  roles: Record<ScenarioKey, Role[]>;
  weeksToGo: number;
  minutesPerDay: number;
}

export const whoOptions = [
  { title: 'I’m still studying IT or CS', short: 'Studying', sub: 'Undergrad, any year', icon: 'grad' },
  { title: 'I graduated and I’m job hunting', short: 'Fresh Graduate', sub: 'Fresh grad, 0–2 years', icon: 'target' },
  { title: 'I already work in tech', short: 'Employed', sub: 'Engineer, analyst, IT pro', icon: 'briefcase' },
] as const;

export const levels = ['New', 'Basic', 'Good', 'Strong'] as const;

export const scenarios: {
  key: ScenarioKey;
  label: string;
  title: string;
  blurb: string;
  heading: string;
}[] = [
  {
    key: 'accelerates',
    label: 'AI accelerates',
    title: 'AI accelerates',
    blurb: 'Agents take over routine coding. People who direct AI do well.',
    heading: 'If AI accelerates, these roles grow, and they fit you.',
  },
  {
    key: 'steady',
    label: 'AI holds steady',
    title: 'AI holds steady',
    blurb: 'Copilots stay helpers. Core engineering still matters most.',
    heading: 'If AI holds steady, these roles stay strong for you.',
  },
  {
    key: 'slows',
    label: 'AI slows down',
    title: 'AI slows down',
    blurb: 'Cost and regulation slow adoption. Fundamentals win.',
    heading: 'If AI slows down, fundamentals carry these roles.',
  },
];

const role = (
  id: string,
  title: string,
  icon: IconName,
  match: number,
  total: number,
  growth: string,
  blurb: string,
  have: string[],
  gap: string[],
  haveCount?: number,
): Role => ({
  id,
  title,
  icon,
  match,
  total,
  growth,
  blurb,
  have,
  gap,
  haveCount: haveCount ?? Math.round((match / 100) * total * 0.6),
});

export const personas: Record<PersonaKey, Persona> = {
  a: {
    key: 'a',
    label: 'A · Undergrad',
    userType: 'USER TYPE 01',
    name: 'Amir, 21',
    age: 21,
    summary: 'Year 3 Computer Science undergrad',
    quote: '“Everyone says AI will write all the code. What am I even studying for?”',
    feels: 'Anxious. Doom-scrolls layoff news.',
    needs: 'Certainty and confidence: proof of what to learn.',
    whoIndex: 0,
    mascotWelcome: 'Hi, I’m Jobee! First, tell me where you are right now.',
    mindBubble: 'You’re not alone. Most CS students we talk to feel the same.',
    timeline: 'Graduating in 2027',
    weeksToGo: 10,
    minutesPerDay: 30,
    roles: {
      accelerates: [
        role('ai-app', 'AI Application Engineer', 'sparkles', 86, 10, '+38% postings by 2028', 'Your Python, APIs and DS&A carry straight over.', ['Python', 'REST APIs'], ['RAG'], 5),
        role('mlops', 'MLOps Engineer', 'cpu', 74, 11, '+29% postings by 2028', 'Strong coding base; deployment is new.', ['Python'], ['Docker', 'CI/CD'], 4),
        role('ai-sec', 'AI Security Analyst', 'shield', 69, 10, '+33% postings by 2028', 'Analytical skills transfer; security is new.', ['Python'], ['Threat modeling', 'LLM risks'], 3),
      ],
      steady: [
        role('backend', 'Backend Engineer', 'layers', 88, 10, '+12% postings by 2028', 'Java, SQL and APIs are exactly what teams hire for.', ['Java', 'SQL & databases'], ['System design'], 6),
        role('data-eng', 'Data Engineer', 'database', 76, 11, '+17% postings by 2028', 'You know SQL and Python; pipelines are the gap.', ['Python', 'SQL & databases'], ['Airflow', 'Data modeling'], 5),
        role('cloud', 'Cloud Engineer', 'cloud', 66, 10, '+15% postings by 2028', 'Good fundamentals; cloud tooling is new.', ['Git & GitHub'], ['AWS basics', 'Linux'], 3),
      ],
      slows: [
        role('backend2', 'Backend Engineer', 'layers', 90, 10, '+8% postings by 2028', 'Fundamentals win when adoption slows.', ['Java', 'Data structures'], ['System design'], 6),
        role('qa', 'Software Engineer in Test', 'bug', 79, 9, '+6% postings by 2028', 'Testing skills sit on top of your coding base.', ['Python', 'Git & GitHub'], ['Test automation'], 5),
        role('dba', 'Database Engineer', 'database', 72, 10, '+5% postings by 2028', 'Your SQL basics grow into core strengths.', ['SQL & databases'], ['Query tuning', 'Replication'], 4),
      ],
    },
  },
  b: {
    key: 'b',
    label: 'B · Fresh grad',
    userType: 'USER TYPE 02',
    name: 'Sara, 24',
    age: 24,
    summary: 'Graduated 8 months ago, still job hunting',
    quote: '“I sent 120 applications. Every junior role now asks for AI experience.”',
    feels: 'Frustrated. Unsure what recruiters want.',
    needs: 'A clear target role and a fast way to close gaps.',
    whoIndex: 1,
    mascotWelcome: 'Hi, I’m Jobee! First, tell me where you are right now.',
    mindBubble: 'Job hunting is tough right now. Let’s find what actually gets interviews.',
    timeline: 'Graduated 8 months ago',
    weeksToGo: 8,
    minutesPerDay: 45,
    roles: {
      accelerates: [
        role('ai-app-b', 'AI Application Engineer', 'sparkles', 82, 10, '+38% postings by 2028', 'Your web and Python skills ship AI features fast.', ['Python', 'REST APIs', 'JavaScript'], ['RAG', 'Prompt engineering'], 5),
        role('fullstack-ai', 'Full-stack Engineer (AI products)', 'layers', 78, 11, '+31% postings by 2028', 'React plus APIs is a strong base; LLM tooling is new.', ['JavaScript', 'React'], ['LLM APIs', 'Evaluation'], 5),
        role('ai-qa', 'AI Quality Engineer', 'bug', 68, 9, '+27% postings by 2028', 'Testing mindset and Git habits transfer.', ['Git', 'Python'], ['Eval design', 'Red teaming'], 3),
      ],
      steady: [
        role('fullstack', 'Full-stack Engineer', 'layers', 86, 10, '+14% postings by 2028', 'You already cover most of what junior roles ask for.', ['JavaScript', 'React', 'SQL'], ['Testing'], 6),
        role('backend-b', 'Backend Engineer', 'database', 74, 10, '+12% postings by 2028', 'Python and SQL are in place; scaling is next.', ['Python', 'SQL & databases'], ['System design', 'Caching'], 4),
        role('devops-b', 'DevOps Engineer', 'cloud', 63, 11, '+16% postings by 2028', 'Git fluency helps; pipelines and cloud are new.', ['Git & GitHub'], ['CI/CD', 'Docker'], 3),
      ],
      slows: [
        role('fullstack2', 'Full-stack Engineer', 'layers', 88, 10, '+9% postings by 2028', 'Core web skills stay in demand.', ['JavaScript', 'React'], ['Testing'], 6),
        role('support-eng', 'Technical Support Engineer', 'bug', 77, 8, '+5% postings by 2028', 'Great entry point that rewards your breadth.', ['Python', 'SQL & databases'], ['Customer comms'], 5),
        role('data-analyst', 'Data Analyst', 'database', 70, 9, '+7% postings by 2028', 'SQL and Python make analytics a short hop.', ['SQL & databases', 'Python'], ['Dashboards', 'Statistics'], 4),
      ],
    },
  },
  c: {
    key: 'c',
    label: 'C · Working engineer',
    userType: 'USER TYPE 03',
    name: 'Daniel, 33',
    age: 33,
    summary: 'Senior Java engineer at a bank, 9 years in',
    quote: '“My team already uses Copilot daily. I’m not sure where I fit in two years.”',
    feels: 'Curious but stretched thin. Little time to study.',
    needs: 'A short, targeted path that builds on 9 years of experience.',
    whoIndex: 2,
    mascotWelcome: 'Hi, I’m Jobee! First, tell me where you are right now.',
    mindBubble: 'Experience counts for a lot. Let’s point it somewhere that lasts.',
    timeline: '9 years in industry',
    weeksToGo: 12,
    minutesPerDay: 25,
    roles: {
      accelerates: [
        role('ai-platform', 'AI Platform Engineer', 'cpu', 84, 11, '+34% postings by 2028', 'Your distributed systems depth is the hard part.', ['Java', 'System design', 'AWS'], ['Model serving', 'Vector DBs'], 7),
        role('ai-arch', 'AI Solutions Architect', 'sparkles', 79, 10, '+30% postings by 2028', 'Architecture and banking domain knowledge stand out.', ['System design', 'Microservices'], ['RAG patterns', 'Governance'], 6),
        role('ai-sec-c', 'AI Security Engineer', 'shield', 71, 10, '+33% postings by 2028', 'Secure-by-design habits transfer directly.', ['Java', 'CI/CD'], ['LLM risks', 'Threat modeling'], 5),
      ],
      steady: [
        role('staff', 'Staff Backend Engineer', 'layers', 90, 10, '+11% postings by 2028', 'You already work at this level; add scale and influence.', ['Java', 'System design', 'Kafka'], ['Org-wide design'], 8),
        role('platform', 'Platform Engineer', 'cloud', 80, 11, '+18% postings by 2028', 'Cloud and CI/CD give you a head start.', ['AWS', 'CI/CD'], ['Kubernetes', 'Terraform'], 6),
        role('data-plat', 'Data Platform Engineer', 'database', 72, 10, '+16% postings by 2028', 'Strong SQL and Kafka; data tooling is new.', ['SQL & databases', 'Kafka'], ['Spark', 'dbt'], 5),
      ],
      slows: [
        role('principal', 'Principal Engineer', 'layers', 91, 10, '+7% postings by 2028', 'Deep experience wins when adoption slows.', ['Java', 'System design'], ['Cross-team strategy'], 8),
        role('eng-manager', 'Engineering Manager', 'shield', 76, 9, '+6% postings by 2028', 'Mentoring history gives you a credible start.', ['Mentoring'], ['Hiring', 'Planning'], 5),
        role('sre', 'Site Reliability Engineer', 'cloud', 73, 10, '+9% postings by 2028', 'Operations know-how plus cloud fundamentals.', ['AWS', 'CI/CD'], ['Observability', 'Incident response'], 5),
      ],
    },
  },
};
