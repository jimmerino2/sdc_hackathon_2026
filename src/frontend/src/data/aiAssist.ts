import type { RoadmapChallenge } from '../api/roadmap';
import { isAiRole, ROLE_AI_GUIDANCE, type RoleAiGuidance } from './aiFluency';
import { skillLabel } from './skills';

/**
 * The AI Assist tips shown inside a challenge. Static and picked by rules, not by a model.
 * In a prompt, {project}, {stack} and {role} are filled in from the challenge; [brackets] are left for the learner.
 * Nothing here touches the rubric, the pass score or stingers.
 */
export interface AssistTip {
  id: string;
  kind: string;
  icon: string;
  title: string;
  advice: string;
  prompt: string;
  why: string;
  /** The AI Fluency lesson that goes deeper. */
  lessonId: string;
  /** Shown only at this stage. */
  stage?: 1 | 2;
  /** Shown only when a skill in the challenge's stack matches. */
  stack?: RegExp;
  /** Shown only for this role. */
  role?: string;
}

export const ASSIST_TIPS: AssistTip[] = [
  {
    id: 'plan-the-brief',
    kind: 'Planning',
    icon: 'target',
    title: 'Turn the brief into a plan',
    advice: 'Before writing code, have AI break the brief into small steps you can build and test one at a time. Then cut or reorder the plan yourself.',
    prompt: `I am building "{project}" using {stack}.

Brief: [paste the project brief]

Do not write code yet. Break this into small steps that can each be built and tested on their own, in a sensible order. For each step, name the files involved and how I can tell it works. Flag anything in the brief that is unclear.`,
    why: 'It separates planning from coding, and each step comes with its own way of checking the result.',
    lessonId: 'ai-assisted-development',
    stage: 1,
  },
  {
    id: 'round-2-changes',
    kind: 'Round 2',
    icon: 'layers',
    title: 'Work out what the new brief changes',
    advice: 'Before touching the code, compare the two briefs. Have AI map what can stay, what must change and what could break, then decide the order yourself so your stage 1 work keeps running.',
    prompt: `"{project}" ({stack}) has a new brief.

Original brief: [paste it]
New brief: [paste it]
Current structure: [the main files and what each does]

Do not write code yet. List what stays, what must change and what might break. Then propose an order of small changes that keeps the project running after each one.`,
    why: 'It gives the model both briefs and the current structure, so the plan builds on your code instead of starting again.',
    lessonId: 'ai-assisted-development',
    stage: 2,
  },
  {
    id: 'frontend-accessibility',
    kind: 'Frontend',
    icon: 'monitor',
    title: 'Review the interface, not only the code',
    advice: 'AI cannot see your page unless you show it. Share the component and a screenshot if your tool accepts images, then check its suggestions with a keyboard and at phone width.',
    prompt: `Here is a component from "{project}": [paste it]

Review it for accessibility and responsive layout: keyboard use, labels, focus states, colour contrast and behaviour at 360px wide. List specific problems with the line each is on. Do not rewrite the component.`,
    why: 'Naming the checks gives specific findings, and asking for no rewrite keeps the change small and yours to apply.',
    lessonId: 'ai-assisted-development',
    stack: /\b(react|vue|angular|svelte|javascript|typescript|html|css|tailwind|next\.?js)\b/i,
  },
  {
    id: 'data-queries',
    kind: 'Data',
    icon: 'database',
    title: 'Give it the schema, then test the query',
    advice: 'Without your schema, AI guesses table and column names. Share the definitions and a few sample rows, and run every query on data where you already know the answer.',
    prompt: `Schema: [paste the table definitions]
Sample rows: [a few made-up rows]
I need: [the question this query must answer]

Write the query and explain each join and filter. Point out how it behaves with NULLs, duplicates and no matching rows, and whether an index would help.`,
    why: 'The schema stops invented columns, and the named edge cases are where queries that look right go wrong.',
    lessonId: 'context-engineering',
    stack: /\b(sql|mysql|postgres(ql)?|sqlite|mongodb|databases?|supabase)\b/i,
  },
  {
    id: 'data-analysis',
    kind: 'Analysis',
    icon: 'chart-bar',
    title: 'Recompute before you report',
    advice: 'AI can suggest analyses quickly, and some of them will be wrong in ways the chart hides. Describe the data, get the code, and recompute one key figure by another route.',
    prompt: `Dataset: [column names, types, row count, a few made-up rows]
Question: [what I want to find out]

Suggest how to analyse this, including data-quality checks to run first. Write the code, state the assumptions behind each step, and name one figure I should recompute separately to confirm the result.`,
    why: 'It puts quality checks before the analysis, and builds an independent check into the answer.',
    lessonId: 'verification-responsible-ai',
    stack: /\b(pandas|numpy|jupyter|tableau|power ?bi|excel|statistics|machine learning|scikit|matplotlib)\b/i,
  },
  {
    id: 'security-review',
    kind: 'Security',
    icon: 'shield',
    title: 'Threat-model it like an attacker',
    advice: 'For a security role, ask AI to attack the design as well as check the code. Then confirm each finding yourself, since it will miss things and invent others.',
    prompt: `Here is how "{project}" handles users' data: [describe the flow, or paste the code]

Act as an attacker. List the most likely ways to misuse this, in order of impact. For each, give the location, how it would work and how to fix it. Say how confident you are, and do not list theoretical issues that do not apply here.`,
    why: 'Ranking by impact and asking for confidence helps you spend your checking time where it counts.',
    lessonId: 'verification-responsible-ai',
    role: '15-1212.00',
  },
  {
    id: 'debugging',
    kind: 'Debugging',
    icon: 'bug',
    title: 'Give it the evidence',
    advice: 'Share the exact error message, the code involved, what you expected and your environment. Ask for the cause before the fix, so you learn something and avoid a rewrite built on a guess.',
    prompt: `Project: "{project}" ({stack})
Code: [paste only the function or file involved]
Expected: [what should happen]
Actual: [the exact error and stack trace]
Environment: [versions, OS, how you run it]
Tried so far: [anything you ruled out]

Identify the most likely root cause and how I can confirm it. Then propose the smallest fix. State your assumptions.`,
    why: 'The evidence replaces guesswork, and asking for the cause first keeps the fix small.',
    lessonId: 'context-engineering',
  },
  {
    id: 'code-generation',
    kind: 'Code generation',
    icon: 'code',
    title: 'Describe the job before asking for code',
    advice: 'State the requirements, constraints, existing structure and the tests it must pass. Ask for one small piece at a time, so that you can read and run each one.',
    prompt: `I am building one feature of "{project}" with {stack}.

Requirement: [what it must do]
Existing structure: [the relevant files and patterns to follow]
Constraints: [libraries allowed, things that must not change]
Tests it must pass: [the cases]

Implement only this feature, in the smallest reasonable change. Explain any decision I should review.`,
    why: 'It gives the model the existing patterns and a definition of done, and it keeps the change small enough to review.',
    lessonId: 'ai-assisted-development',
  },
  {
    id: 'testing',
    kind: 'Testing',
    icon: 'check',
    title: 'Ask what could break',
    advice: 'Have AI list edge cases before it writes tests, then check for gaps. Good tests come from the requirement. Tests written only from the code can repeat its bugs.',
    prompt: `Requirement: [what the code must do]
Code: [paste it]

First list the edge cases and failure modes, including bad input. Mark which ones the code does not handle. Then write unit tests for the most important ones, with a note on what each proves and what is still not covered.`,
    why: 'Listing cases first exposes missing behaviour, and asking what is not covered stops a passing suite looking more complete than it is.',
    lessonId: 'ai-assisted-development',
  },
  {
    id: 'code-review',
    kind: 'Code review',
    icon: 'search',
    title: 'Treat a review as suggestions',
    advice: 'Ask for security, performance and maintainability concerns, and decide on each one yourself. Some will be wrong or not worth doing here, and rejecting those is part of the job.',
    prompt: `Review this code from "{project}" as a careful senior {role}: [paste the diff or files]

Look for security issues, performance problems and anything hard to maintain. For each, give the location, why it matters and how confident you are. Skip style comments.`,
    why: 'Location and confidence make each finding quick to check, and skipping style keeps the list short.',
    lessonId: 'verification-responsible-ai',
  },
];

/** How to check anything AI gives you for a challenge. */
export const ASSIST_CHECKLIST = [
  'I ran the code myself and tried the main flows',
  'I can explain every part of it without the AI',
  'The tests fail when I break the code on purpose',
  'Any new package exists and comes from a trusted source',
  'No keys, passwords or personal data are in the repo',
  'It does what the brief asks, not only what the prompt asked',
];

export const REFLECTION_QUESTIONS = [
  { key: 'used', label: 'What did you use AI for?' },
  { key: 'verified', label: 'What did you independently verify?' },
  { key: 'changed', label: 'What suggestions did you change or reject?' },
] as const;

export type ChallengeContext = Pick<RoadmapChallenge, 'title' | 'stage' | 'onet_code' | 'role_title' | 'tech_stack'>;

function fillPrompt(prompt: string, c: ChallengeContext, stack: string[]): string {
  return prompt
    .replaceAll('{project}', c.title)
    .replaceAll('{stack}', stack.join(', ') || 'my chosen stack')
    .replaceAll('{role}', c.role_title);
}

/** The tips for one challenge: stage and stack or role tips first, then the core four, with their prompts filled in. */
export function tipsFor(c: ChallengeContext): AssistTip[] {
  const stack = c.tech_stack.flatMap((a) => a.skills.map(skillLabel));
  return ASSIST_TIPS
    .filter((t) => (t.stage ?? c.stage) === c.stage && (t.role ?? c.onet_code) === c.onet_code && (!t.stack || stack.some((s) => t.stack!.test(s))))
    .map((t) => ({ ...t, prompt: fillPrompt(t.prompt, c, stack) }));
}

/** The role's static AI guidance, for tech roles. */
export const guidanceFor = (onetCode: string): RoleAiGuidance | null => (isAiRole(onetCode) ? ROLE_AI_GUIDANCE[onetCode] : null);
