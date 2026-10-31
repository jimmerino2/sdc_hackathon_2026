/**
 * The AI Fluency curriculum: curated, hardcoded lessons shown in the Learn page's optional section.
 * To add a lesson, add an entry to AI_LESSONS; the section and lesson page render whatever is here.
 * Each lesson follows concept, why it matters, demonstration, application, verification, further reading.
 */

/** Jobee's eight tech roles (TECH_ROLES in the backend's jobs/service.py), by O*NET code. */
export const AI_ROLE_CODES = [
  '15-1211.00', '15-1212.00', '15-1232.00', '15-1252.00', '15-1255.00', '15-2031.00', '15-2051.00', '15-2051.01',
] as const;
export type AiRoleCode = (typeof AI_ROLE_CODES)[number];

export interface LessonSection {
  heading: string;
  body?: string[];
  bullets?: string[];
  /** A numbered framework or workflow. */
  steps?: { name: string; detail: string }[];
  /** A caveat shown under the section. */
  note?: string;
}

export interface LessonExample {
  title: string;
  /** The situation, when the example needs one. */
  context?: string;
  /** Left out when the example is a single good prompt. */
  before?: string;
  after: string;
  /** Default to "Weak prompt" and "Stronger prompt". */
  beforeLabel?: string;
  afterLabel?: string;
  why: string;
}

export interface PromptTemplate {
  title: string;
  prompt: string;
  /** Why this prompt works. */
  why: string;
}

export interface LessonExercise {
  task: string;
  steps: string[];
  doneWhen: string;
}

export interface FurtherReading {
  label: string;
  url: string;
  note: string;
  licence?: string;
}

export interface AiLesson {
  id: string;
  title: string;
  summary: string;
  category: string;
  difficulty: 'Beginner' | 'Intermediate';
  minutes: number;
  objectives: string[];
  why: string[];
  sections: LessonSection[];
  examples: LessonExample[];
  templates: PromptTemplate[];
  exercise: LessonExercise;
  checklist: string[];
  reading: FurtherReading[];
  /** The roles this lesson is most useful for, beyond being open to everyone. */
  roles: readonly AiRoleCode[];
  tags: string[];
}

const READING = {
  unesco: { label: 'UNESCO AI Competency Framework for Students', url: 'https://www.unesco.org/en/articles/ai-competency-framework-students', note: 'What AI competence means beyond tool skills: human agency, ethics and critical use.' },
  microsoft: { label: 'Microsoft Generative AI for Beginners', url: 'https://github.com/microsoft/generative-ai-for-beginners', note: 'A free open course, for going deeper on building with language models.', licence: 'MIT licence, Microsoft. Linked, not republished.' },
  dair: { label: 'DAIR.AI Prompt Engineering Guide', url: 'https://www.promptingguide.ai/', note: 'A vendor-neutral catalogue of prompting techniques with examples.', licence: 'MIT licence, DAIR.AI. Linked, not republished.' },
  openai: { label: 'OpenAI: Prompt engineering', url: 'https://developers.openai.com/api/docs/guides/prompt-engineering', note: 'Guidance on structuring instructions, from a model provider.' },
  anthropic: { label: 'Anthropic: Prompt engineering overview', url: 'https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview', note: 'Techniques for being clear, giving examples and structuring prompts.' },
  google: { label: 'Google: Gemini prompting strategies', url: 'https://ai.google.dev/gemini-api/docs/prompting-strategies', note: 'Another provider’s view; compare it with the others to see what transfers.' },
  vscode: { label: 'VS Code: AI agent best practices', url: 'https://code.visualstudio.com/docs/agents/best-practices', note: 'Working practices for coding agents inside an editor.' },
  mcp: { label: 'Model Context Protocol: introduction', url: 'https://modelcontextprotocol.io/docs/getting-started/intro', note: 'The protocol’s own introduction to clients, servers and tools.' },
  owasp: { label: 'OWASP Top 10 for LLM Applications', url: 'https://genai.owasp.org/llm-top-10/', note: 'The main security risks in software built on language models.' },
  nist: { label: 'NIST AI Risk Management Framework', url: 'https://www.nist.gov/itl/ai-risk-management-framework', note: 'A structured way for organisations to think about AI risk.' },
} satisfies Record<string, FurtherReading>;

export const AI_LESSONS: AiLesson[] = [
  {
    id: 'prompting-fundamentals',
    title: 'Prompting Fundamentals',
    summary: 'Turn a vague request into an instruction that gets usable work back on the first or second try.',
    category: 'Foundations',
    difficulty: 'Beginner',
    minutes: 20,
    objectives: [
      'Write a prompt that states the task, context, constraints and output format',
      'Use the six-part checklist to find what a weak prompt is missing',
      'Improve a result by changing the prompt, rather than retrying it unchanged',
    ],
    why: [
      'A model only knows what is in front of it. It has not seen your ticket, your team’s conventions or who will read the result, so it fills the gaps with plausible defaults.',
      'Those defaults are where most disappointing answers come from. Stating what you need takes a minute and usually saves several rounds of correction.',
    ],
    sections: [
      {
        heading: 'What separates a good prompt',
        bullets: [
          'A clear task: one verb and one outcome. “Summarise this incident for the support team” beats “thoughts on this?”',
          'Relevant context: who it is for, what it feeds into, what has been tried.',
          'Constraints: length, tools allowed, things to avoid, the version you are on.',
          'An output format: a table with named columns, a diff, five bullets, JSON matching a shape.',
          'An example, when the format or tone is hard to describe. One good sample often beats a paragraph of description.',
          'Iteration: read the result, say exactly what was wrong, and adjust.',
        ],
      },
      {
        heading: 'A prompt-building checklist',
        body: ['Run through these before you send anything that matters.'],
        steps: [
          { name: 'Goal', detail: 'What do you want the AI to accomplish?' },
          { name: 'Context', detail: 'What background information does it need?' },
          { name: 'Inputs', detail: 'What information or materials should it work with?' },
          { name: 'Constraints', detail: 'What limitations or rules must it follow?' },
          { name: 'Output', detail: 'What format or deliverable do you expect?' },
          { name: 'Verification', detail: 'How should the result be checked?' },
        ],
        note: 'This is a useful checklist, not a mandatory formula. A one-line question can be the right prompt. Use the parts the task needs and skip the rest.',
      },
      {
        heading: 'Iterate on the instruction',
        body: [
          'When a result misses, name the miss: “The tone is too formal, and you dropped the rollback step.” Regenerating the same prompt only rolls the dice again.',
          'If a conversation has gone in circles, start a new one with a better first prompt. Carrying over the wrong turns tends to make things worse.',
        ],
      },
    ],
    examples: [
      {
        title: 'Writing a release note',
        context: 'You shipped a change to password reset and need a note for customers.',
        before: 'Write release notes for the password reset update.',
        after: `Write a release note for customers of a project-management app.

Goal: tell them what changed and whether they need to do anything.
Context: non-technical readers, most on the free plan.
Inputs: the change list below.
Constraints: under 80 words, no internal ticket numbers, no blame for the old behaviour.
Output: a one-line heading, then up to three bullets.
Verification: list anything you assumed that is not in the change list.

Change list:
- Reset links now expire after 30 minutes instead of 24 hours
- Fixed reset emails going out twice`,
        why: 'The second prompt fixes the audience, length and format, supplies the facts so nothing gets invented, and asks the model to flag its assumptions. That last line makes the result quicker to check.',
      },
    ],
    templates: [
      {
        title: 'General task prompt',
        prompt: `Goal: [what you want done, in one sentence]
Context: [who it is for and why it is needed]
Inputs: [paste the material to work from]
Constraints: [length, tools, things to avoid]
Output: [the exact format you want]
Verification: Before you answer, list any assumptions you made and anything you could not determine from the inputs.`,
        why: 'It forces you to supply what the model cannot guess, and the last line brings its assumptions into the open where you can check them.',
      },
    ],
    exercise: {
      task: 'Take a prompt you used recently that gave a disappointing answer, or use: “Explain our API to a new developer.”',
      steps: [
        'Mark which of the six checklist parts are missing.',
        'Rewrite it, adding only the parts that would change the answer.',
        'Run both versions in any AI assistant and compare them.',
      ],
      doneWhen: 'You can point to a specific difference in the output and name the line of your prompt that caused it.',
    },
    checklist: [
      'Does the output do what the goal asked, for the audience you named?',
      'Does it respect every constraint? Count the words or items if it matters.',
      'Is every fact traceable to your inputs, or to a source you can check?',
      'Did you read the assumptions it listed, and correct any wrong ones?',
    ],
    reading: [READING.dair, READING.anthropic, READING.openai, READING.google],
    roles: AI_ROLE_CODES,
    tags: ['prompting', 'communication', 'iteration'],
  },
  {
    id: 'context-engineering',
    title: 'Context Engineering',
    summary: 'Give the model the right information, in the right amount, instead of writing longer prompts.',
    category: 'Foundations',
    difficulty: 'Beginner',
    minutes: 25,
    objectives: [
      'Choose which files, errors and constraints a task needs',
      'Split a large task into steps that each carry their own context',
      'Spot when a conversation has drifted, and restart it cleanly',
    ],
    why: [
      'A perfectly worded prompt about code the model cannot see will still produce a guess. On real work, what the model has been shown matters more than how you phrased the request.',
      'More is not better. Irrelevant files bury the part that matters and use up a limited context window, and pasting a whole repository can expose things that should stay private.',
    ],
    sections: [
      {
        heading: 'What counts as context',
        bullets: [
          'Files and documents: the function that fails, the spec it should meet, the schema it reads.',
          'Code and errors: the exact message and stack trace, not a paraphrase.',
          'Architecture and constraints: framework versions, patterns the project follows, what must not change.',
          'Conversation history: earlier decisions the model should keep to.',
        ],
      },
      {
        heading: 'Select, then supply',
        steps: [
          { name: 'Start from the failure or the goal', detail: 'Ask what someone would need to open to work on this. Include that and leave out the rest.' },
          { name: 'Include the contract', detail: 'Expected behaviour, actual behaviour, and the types or interfaces around the code.' },
          { name: 'State what is fixed', detail: 'Dependencies you cannot change, style rules, and behaviour that must stay the same.' },
          { name: 'Let the model ask', detail: 'End with “Ask me for anything you need before you start.” Supply missing information as it comes up.' },
        ],
      },
      {
        heading: 'Break complex work into steps',
        body: [
          'A large task in one prompt tends to return a large, shallow answer. Split it: understand, then plan, then change one thing, then test it. Each step gets the context it needs and gives you a place to catch a mistake early.',
          'When a conversation gets long or wanders, ask for a summary of decisions so far and paste that into a fresh conversation. You keep the conclusions and drop the noise.',
        ],
        note: 'Assistants differ in how much they keep and whether they can read your files directly. Check what yours can see instead of assuming it knows your project.',
      },
    ],
    examples: [
      {
        title: 'Debugging a Python function',
        before: 'Fix my code.',
        after: 'Here is the relevant Python function, its expected behaviour, the actual error and the dependencies being used. Identify the likely root cause before proposing a minimal fix. Explain any assumptions.',
        why: 'The second version gives the model what it needs to reason, asks for a diagnosis before a change, and limits the fix to the smallest one. That stops it rewriting working code around a guess.',
      },
      {
        title: 'Filled in with real detail',
        context: 'The same pattern in practice, for a date-parsing bug in a Flask app.',
        after: `Function (app/reports.py):
def month_key(raw):
    return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m")

Expected: "2026-03-01" returns "2026-03".
Actual: ValueError: unconverted data remains: T09:15:00Z
Input comes from a third-party webhook; some rows include a time, some do not.
Environment: Python 3.12, Flask 3. Standard library only.

Identify the likely root cause before proposing a minimal fix. Explain any assumptions.`,
        afterLabel: 'Prompt with context',
        why: 'Six lines of context are enough. The model gets the code, the failing input, how it arrived and the dependency limit, without seeing the rest of the app.',
      },
      {
        title: 'Too much is also a mistake',
        before: 'Here is our entire repository as a zip, plus the .env file. Why is checkout slow?',
        after: `Checkout takes about 4 seconds on carts with over 50 items. Here are the handler, the two queries it runs and a profiler trace of one slow request. Which of these is the most likely cause, and what would you measure next to confirm it?`,
        why: 'The first dumps everything and leaks credentials. The second sends only what relates to the symptom, includes a measurement, and asks for a next step you can check.',
      },
    ],
    templates: [
      {
        title: 'Debugging with context',
        prompt: `Code: [paste only the function or file involved]
Expected behaviour: [what should happen]
Actual behaviour: [the exact error message and stack trace]
How to reproduce: [the input or steps]
Environment: [language, framework and library versions]
What I have tried: [anything you already ruled out]

Identify the most likely root cause and how you would confirm it. Then propose the smallest fix. State any assumptions, and ask if you need to see another file.`,
        why: 'It separates diagnosis from the fix, and invites a request for more context instead of a confident guess.',
      },
      {
        title: 'Restarting a long conversation',
        prompt: 'Summarise this conversation for a colleague taking over: the goal, the decisions made and why, what has been tried and failed, and what remains. Keep exact names of files, functions and versions.',
        why: 'It moves the useful conclusions into a new conversation and leaves the failed attempts behind.',
      },
    ],
    exercise: {
      task: 'Pick a bug you fixed recently, or one open in a project of yours.',
      steps: [
        'Write down the minimum someone would need to see to diagnose it.',
        'Write the prompt using the debugging template, without pasting anything else.',
        'Remove one piece of context at a time and decide whether the answer would change.',
      ],
      doneWhen: 'Your prompt fits on one screen, contains no secrets, and still gives the model enough to name the real cause.',
    },
    checklist: [
      'Is everything you shared needed, and safe to share?',
      'Does the diagnosis match the actual error message and your reproduction?',
      'Did it name the files or functions you gave it, not ones it made up?',
      'Are its assumptions true of your project and versions?',
    ],
    reading: [READING.anthropic, READING.dair, READING.vscode],
    roles: ['15-1252.00', '15-1211.00', '15-1232.00', '15-2051.00'],
    tags: ['context', 'debugging', 'repository context'],
  },
  {
    id: 'ai-assisted-development',
    title: 'AI-Assisted Software Development',
    summary: 'Work with a coding assistant in small, reviewed steps, and stay the author of what ships.',
    category: 'Applied',
    difficulty: 'Intermediate',
    minutes: 30,
    objectives: [
      'Use an assistant to read unfamiliar code, plan changes and write tests',
      'Follow a seven-step workflow that keeps each change small and reviewed',
      'Ask for a review that surfaces real security and maintainability risks',
    ],
    why: [
      'Coding assistants are fast at producing code that looks finished. The risk has moved from writing it to knowing whether it is right.',
      'Reviewing a 600-line change you did not write is harder than reviewing six small ones. The habits below keep the speed and leave you able to explain every change.',
    ],
    sections: [
      {
        heading: 'Where an assistant helps',
        bullets: [
          'Understanding unfamiliar code: “Trace what happens from this route to the database, and name the files involved.”',
          'Generating code: give requirements, the existing pattern to follow and the tests it must pass.',
          'Debugging: supply the error, the code and the environment, and ask for a cause before a fix.',
          'Refactoring: state that behaviour must not change, and get tests in place first.',
          'Unit tests and edge cases: ask what could break before asking for test code.',
          'Code review and security: ask for specific risks, then judge each one yourself.',
        ],
      },
      {
        heading: 'A recommended workflow',
        steps: [
          { name: 'Understand the task', detail: 'Restate it in your own words. If you cannot, ask questions before any code exists.' },
          { name: 'Ask AI to propose an implementation plan', detail: 'Files to touch, the approach, and the risks. No code yet.' },
          { name: 'Review the proposed approach', detail: 'Check it against how the project already works. Cheap to change now, expensive later.' },
          { name: 'Implement incrementally', detail: 'One step at a time, each small enough to read, run and commit on its own.' },
          { name: 'Generate and run tests', detail: 'Run them yourself. Passing means nothing if the tests only repeat what the code does.' },
          { name: 'Review the generated changes', detail: 'Read the diff line by line, as you would a colleague’s. Delete what you cannot explain.' },
          { name: 'Verify that the implementation actually meets requirements', detail: 'Go back to the original task and try it the way a user would.' },
        ],
        note: 'Tools that edit files or run commands by themselves make this more important. Review what an agent plans to do, and keep your work in version control so every step can be undone.',
      },
    ],
    examples: [
      {
        title: 'Adding pagination to an API',
        context: 'Your team’s GET /orders endpoint returns every order and has started timing out. You are asked to add pagination.',
        before: 'Add pagination to my orders endpoint.',
        after: `I need to add pagination to GET /orders in a FastAPI service. Do not write code yet.

Current handler: [paste it]
Query it runs: [paste it]
How another endpoint paginates: [paste GET /customers]

Requirements:
- Follow the same pattern as /customers
- Default page size 50, maximum 200
- Keep the response shape for existing clients
- Results must stay stable while new orders arrive

Propose a plan: the files to change, the approach and what could go wrong. Then list the test cases you would add, including edge cases.`,
        why: 'It holds back code until the plan is agreed, points to an existing pattern so the change fits in, and raises the awkward requirement of stability under new inserts, which is where a simple offset approach can fall down.',
      },
    ],
    templates: [
      {
        title: 'Plan before code',
        prompt: `Task: [what needs to change and why]
Relevant code: [paste the files or point to them]
Patterns to follow: [an existing example in this project]
Must not change: [public APIs, behaviour, dependencies]

Do not write code yet. Propose a plan: the files to change, the approach, any alternatives you rejected and why, the risks, and the tests you would add. Ask about anything unclear.`,
        why: 'Reviewing a plan takes minutes, and it catches a wrong approach before there is a large diff to unpick.',
      },
      {
        title: 'Review a change',
        prompt: `Review this change as a careful senior engineer. Here is the requirement: [paste it]. Here is the diff: [paste it].

Look for: bugs and missed edge cases, security issues, performance problems, and anything hard to maintain.
For each finding, give the location, why it matters and how sure you are. Do not comment on style. If something is fine, say nothing about it.`,
        why: 'Asking for location and confidence makes findings easy to verify, and ruling out style removes noise.',
      },
    ],
    exercise: {
      task: 'Add one small feature or fix to a project of yours by following the seven steps.',
      steps: [
        'Get a plan from an assistant before any code, and change at least one thing in it.',
        'Implement in at least two separate commits.',
        'Write down one thing the review found, and whether you accepted it.',
      ],
      doneWhen: 'You can explain every line in the diff, and you have tried the feature yourself on top of the tests passing.',
    },
    checklist: [
      'Have you read the whole diff, and can you explain every line?',
      'Did you run the code and tests yourself?',
      'Do the tests fail when you break the code on purpose?',
      'Do any new packages exist, come from a trusted source and fit the project?',
      'Are inputs validated, and are secrets kept out of the code?',
      'Does the result meet the original requirement, not just the tests?',
    ],
    reading: [READING.vscode, READING.microsoft, READING.owasp],
    roles: ['15-1252.00', '15-1255.00', '15-1212.00'],
    tags: ['coding assistants', 'testing', 'code review', 'agentic workflows'],
  },
  {
    id: 'tools-integrations-workflows',
    title: 'AI Tools, Integrations and Workflows',
    summary: 'Know which capability fits a task, and how to combine them without losing control.',
    category: 'Applied',
    difficulty: 'Intermediate',
    minutes: 25,
    objectives: [
      'Match a task to the right AI capability',
      'Explain what connectors, MCP and agents do, and the risks they add',
      'Design a multi-step workflow with human checkpoints',
    ],
    why: [
      'The same assistant can look brilliant or useless depending on whether it has the right capability for the job. Asking a model to recall last week’s release notes from memory is a different act from letting it search for them.',
      'These capabilities are named differently across products and change often. Learn what each one does, then check what your own tools offer.',
    ],
    sections: [
      {
        heading: 'Capabilities, and when each is useful',
        bullets: [
          'General-purpose assistants: drafting, explaining and thinking a problem through. Treat factual recall as unverified.',
          'Web search and research: anything recent or needing a source. Open the sources yourself.',
          'File and document analysis: asking questions of a long spec, contract or report you supply.',
          'Code execution and data analysis: calculations and charts. Running code is more reliable than the model doing arithmetic in its head, if you check the code.',
          'Image, audio and multimodal: reading a screenshot of an error, transcribing a meeting, describing a diagram.',
          'AI coding assistants: working inside your editor or terminal with access to your project.',
          'Connectors and integrations: reading from or acting in your calendar, tickets, databases or repositories.',
          'Agents and workflow automation: a model that plans and takes several steps using tools, with less supervision per step.',
        ],
        note: 'Availability varies by product, plan and organisation policy. Nothing in this lesson requires a particular provider or paid plan.',
      },
      {
        heading: 'MCP, briefly',
        body: [
          'The Model Context Protocol (MCP) is an open standard for connecting AI applications to tools and data. An MCP server exposes capabilities, such as searching tickets or querying a database, and any compatible client can use them. It works a little like a common plug: one connector can serve several applications, without a custom integration for each pair.',
          'Support differs between products, so check before relying on it. A connected server should be treated like any other software you install: find out who wrote it and what it can touch.',
        ],
      },
      {
        heading: 'Agents and the checkpoints they need',
        body: ['An agent loops: decide on a step, use a tool, look at the result, decide again. That is useful for multi-step work, and every extra step is another chance to go wrong unnoticed.'],
        bullets: [
          'Give the least access that does the job. Read-only is a good default.',
          'Require approval for anything hard to undo: deleting, sending, paying, deploying.',
          'Treat content from web pages, emails and tickets as untrusted. It can contain instructions aimed at the model, known as prompt injection.',
          'Keep a record of what was done, so it can be reviewed and reversed.',
        ],
      },
    ],
    examples: [
      {
        title: 'Investigating an outage',
        context: 'Support reports failed payments since this morning. Capabilities working together, with a person checking between steps.',
        after: `1. Connector: pull the error tickets from the last 12 hours.
2. Code execution: group them by time and error code, and chart them.
3. Coding assistant: read the deploys around the spike. Which change is the likely cause?
4. You: reproduce it and confirm the cause before acting.
5. General assistant: draft the customer update and post-incident notes from the verified facts.`,
        afterLabel: 'Workflow',
        why: 'Each capability does what it is good at, and the human checkpoint sits before anything reaches customers. A model’s theory is only a theory until step 4.',
      },
      {
        title: 'Comparing database options',
        context: 'You need a short recommendation on two managed databases for your team.',
        after: `1. Web search: find each product’s current pricing and limits from official pages.
2. File analysis: check your requirements document against those limits.
3. Code execution: model monthly cost at your actual traffic.
4. General assistant: draft a one-page recommendation that cites each source.
5. You: open every source and check the numbers before sending.`,
        afterLabel: 'Workflow',
        why: 'Search supplies current facts, code does the arithmetic, and the draft cites sources, so the final check takes minutes.',
      },
    ],
    templates: [
      {
        title: 'Design a workflow',
        prompt: `I want to get this done: [the task and its end result].
Tools I have: [the assistant, search, file upload, code execution, connectors available to me]
Data involved: [what it is, and how sensitive it is]

Propose a step-by-step workflow. For each step, name the capability used, its input and its output, and mark where a person must check the result. Point out any step that cannot be undone or that handles sensitive data.`,
        why: 'It makes the model plan around what you actually have, and puts checkpoints and risks in the design.',
      },
    ],
    exercise: {
      task: 'Pick a repetitive task from your studies or work that takes at least 30 minutes.',
      steps: [
        'Split it into steps and name the capability that suits each.',
        'Mark the steps that need a person, and the ones that cannot be undone.',
        'Try one step with a tool you have, and note where it needed correction.',
      ],
      doneWhen: 'You have a written workflow with at least one human checkpoint, and evidence from one real step.',
    },
    checklist: [
      'Did the tool use a current source, or answer from memory?',
      'If code ran, did you read the code and sanity-check the numbers?',
      'What does each connector or agent have access to, and is that the minimum?',
      'Is there a human check before anything sent, deleted or deployed?',
      'Could outside content have steered the result?',
    ],
    reading: [READING.mcp, READING.vscode, READING.owasp, READING.microsoft],
    roles: ['15-1211.00', '15-1232.00', '15-2051.01', '15-2031.00'],
    tags: ['tools', 'connectors', 'MCP', 'agents', 'workflow automation'],
  },
  {
    id: 'verification-responsible-ai',
    title: 'Verification and Responsible AI',
    summary: 'Catch convincing mistakes, protect sensitive data, and stay accountable for your work.',
    category: 'Judgement',
    difficulty: 'Beginner',
    minutes: 25,
    objectives: [
      'Recognise the ways AI output can look right and be wrong',
      'Check claims, code and analysis using methods that fit each',
      'Decide what must not be shared with an AI tool, and when a person must decide',
    ],
    why: [
      'A model’s tone does not change with its accuracy. A fabricated reference and a real one read exactly the same.',
      'Your name goes on the work. “The AI said so” will not satisfy a reviewer, a client or an auditor, so being able to check output is the skill that makes the rest safe to use.',
    ],
    sections: [
      {
        heading: 'How convincing mistakes happen',
        bullets: [
          'Hallucinations: invented facts, citations, functions or packages, stated with confidence.',
          'Unsupported assumptions: a gap filled quietly with something plausible.',
          'Bias: skewed patterns from training data, such as in hiring or lending examples, presented as neutral.',
          'Outdated information: answers that were true for an older version.',
        ],
      },
      {
        heading: 'Match the check to the output',
        bullets: [
          'Facts and figures: find the primary source and open it. A link in the answer is not proof until you have read it.',
          'Code: read it, run it, test it, and try inputs that should fail.',
          'Analysis: recompute one number by hand, and check the data was what you think it was.',
          'Recommendations: ask what would make this wrong, and who it might disadvantage.',
        ],
        note: 'Asking the same model “are you sure?” is not verification. It can help surface doubts, but only an independent source or a test can confirm anything.',
      },
      {
        heading: 'Protect information',
        bullets: [
          'Never paste passwords, API keys, tokens or private keys. If one leaks, rotate it.',
          'Follow your employer’s or university’s policy on approved tools before sharing internal code or documents.',
          'Remove personal data, or replace it with made-up values, unless you have approval to process it.',
          'Check whether your tool retains data or uses it for training. It depends on the product and plan.',
        ],
      },
      {
        heading: 'Copyright and human judgement',
        body: [
          'Rules on AI-generated content and its copyright differ by country and are still developing, so check your organisation’s or course’s policy. Do not ask a tool to reproduce someone’s work, and respect the licences of code you reuse. Disclose AI use where your course, client or employer requires it.',
          'Keep a person in charge of decisions that affect people: hiring, grades, medical or legal questions, security sign-off, anything hard to reverse. AI can inform these decisions, but someone accountable has to make them.',
        ],
      },
    ],
    examples: [
      {
        title: 'Code that works and is still wrong',
        context: 'An assistant writes a login lookup. The demo runs and the happy-path test passes.',
        before: `query = f"SELECT * FROM users WHERE email = '{email}'"
cursor.execute(query)`,
        beforeLabel: 'Looks fine',
        after: `cursor.execute("SELECT * FROM users WHERE email = %s", (email,))`,
        afterLabel: 'After review',
        why: 'The first version builds SQL from user input, so a crafted email can change the query. Tests with normal emails never reveal this. Parameterised queries fix it, and the check that finds it is reading the code with an attacker in mind.',
      },
      {
        title: 'A package that may not exist',
        context: 'An assistant suggests a neat library for your task.',
        before: 'Run: pip install fastapi-easy-ratelimiter',
        beforeLabel: 'Sounds real',
        after: `Before installing:
1. Search the registry. Does it exist?
2. Check the owner, repository, downloads and last release.
3. Compare the name carefully with the well-known package you expected.`,
        afterLabel: 'After checking',
        why: 'Models invent plausible package names, and attackers have registered such names with malicious code. An install command can run someone else’s code on your machine, so a two-minute check is worthwhile. The name above is only an illustration.',
      },
      {
        title: 'A statistic with a source attached',
        context: 'You ask for evidence for a slide.',
        before: 'A 2023 study in the Journal of Applied Software Research found that teams using AI tools ship 47% faster.',
        beforeLabel: 'Looks sourced',
        after: `Search for the title and journal directly. Then check:
- Does the paper exist?
- Does it say this, about these people, under these conditions?
- Who funded it?
If you cannot find it, remove the claim.`,
        afterLabel: 'After checking',
        why: 'Specific numbers and journal names make a claim feel checked, but the sentence above is invented for this lesson. That is the point: nothing in the wording gives it away. Only opening the source can.',
      },
    ],
    templates: [
      {
        title: 'Find the weak points',
        prompt: `Here is a piece of work: [paste the code, analysis or text].

List the claims or behaviours in it that most need checking. For each, say what could be wrong, how I could verify it independently, and how confident you are. Mark anything you cannot support from what I gave you.`,
        why: 'It does not ask the model to vouch for itself. It produces a list of checks that you carry out yourself.',
      },
      {
        title: 'Check for bias and assumptions',
        prompt: `Here is a recommendation: [paste it]. It affects: [the people affected].

What assumptions does it depend on? Which groups might it serve poorly, and why? What data would show whether those concerns are real?`,
        why: 'It turns “is this fair?” into specific assumptions and data you can examine, leaving the decision with you.',
      },
    ],
    exercise: {
      task: 'Ask an AI assistant for a short technical explanation with sources, on a topic you know reasonably well.',
      steps: [
        'Highlight every checkable claim.',
        'Open each source and check that it exists and says what was claimed.',
        'Write down what was accurate, what was unsupported and what was wrong.',
      ],
      doneWhen: 'Every claim is marked verified, unsupported or wrong, with the evidence you used.',
    },
    checklist: [
      'Did you open every source you are relying on?',
      'Did you run the code, including inputs that should fail?',
      'Did you recompute at least one important number yourself?',
      'Is there any secret, personal or confidential data in what you shared?',
      'Who could be harmed if this is wrong, and has a person reviewed it?',
      'Would you be comfortable explaining and defending this work without the tool?',
    ],
    reading: [READING.unesco, READING.nist, READING.owasp, READING.microsoft],
    roles: AI_ROLE_CODES,
    tags: ['verification', 'responsible AI', 'privacy', 'security'],
  },
];

/** Static guidance for each tech role. Educational only: it never feeds match scores or their weights. */
export interface RoleAiGuidance {
  title: string;
  /** The AI skills most worth building in this role. */
  skills: string[];
  /** Lessons to start with, in order. */
  lessons: string[];
  /** A concrete way to use AI in this role, and what to check. */
  useCase: string;
}

export const ROLE_AI_GUIDANCE: Record<AiRoleCode, RoleAiGuidance> = {
  '15-1252.00': {
    title: 'Software Developers',
    skills: ['AI-assisted development', 'Debugging and code review', 'Test generation', 'Repository context management', 'Agentic coding workflows'],
    lessons: ['ai-assisted-development', 'context-engineering', 'verification-responsible-ai'],
    useCase: 'Ask for a plan before code on your next ticket, then review the diff as you would a colleague’s.',
  },
  '15-2051.00': {
    title: 'Data Scientists',
    skills: ['AI-assisted exploratory data analysis', 'Hypothesis generation', 'Data cleaning', 'Statistical verification', 'Model evaluation'],
    lessons: ['context-engineering', 'tools-integrations-workflows', 'verification-responsible-ai'],
    useCase: 'Describe a dataset’s columns and ask for hypotheses to test, then recompute any result you plan to report.',
  },
  '15-2051.01': {
    title: 'Business Intelligence Analysts',
    skills: ['Drafting and explaining SQL', 'Data modelling review', 'Dashboard narrative writing', 'Metric definition checks', 'Reconciling figures to source'],
    lessons: ['prompting-fundamentals', 'tools-integrations-workflows', 'verification-responsible-ai'],
    useCase: 'Give the table definitions and ask for a query with its reasoning, then reconcile the total against a known report.',
  },
  '15-1211.00': {
    title: 'Computer Systems Analysts',
    skills: ['Requirements summarising', 'Process mapping', 'Comparing solution options', 'Reading unfamiliar systems', 'Stakeholder communication'],
    lessons: ['prompting-fundamentals', 'tools-integrations-workflows', 'context-engineering'],
    useCase: 'Turn meeting notes into draft requirements, marking each one as stated or assumed, then confirm them with stakeholders.',
  },
  '15-1212.00': {
    title: 'Information Security Analysts',
    skills: ['Log and alert triage', 'Secure code review', 'Threat modelling support', 'Prompt injection awareness', 'Data handling policy'],
    lessons: ['verification-responsible-ai', 'ai-assisted-development', 'tools-integrations-workflows'],
    useCase: 'Ask for a threat model of a sanitised design, then check each finding yourself. Never paste real credentials or customer logs into an unapproved tool.',
  },
  '15-1232.00': {
    title: 'Computer User Support Specialists',
    skills: ['Troubleshooting with screenshots and logs', 'Knowledge base drafting', 'Clear customer replies', 'Ticket summarising', 'Knowing when to escalate'],
    lessons: ['prompting-fundamentals', 'context-engineering', 'verification-responsible-ai'],
    useCase: 'Remove personal details from a ticket, ask for likely causes in order, and test each fix before suggesting it to a user.',
  },
  '15-1255.00': {
    title: 'Web and Digital Interface Designers',
    skills: ['Front-end prototyping', 'Accessibility review', 'Copy and content variants', 'Design critique prompts', 'Responsive layout debugging'],
    lessons: ['prompting-fundamentals', 'ai-assisted-development', 'verification-responsible-ai'],
    useCase: 'Ask for an accessibility review of a component, then confirm it with a keyboard and a contrast checker.',
  },
  '15-2031.00': {
    title: 'Operations Research Analysts',
    skills: ['Formulating optimisation models', 'Simulation code support', 'Sensitivity analysis', 'Assumption testing', 'Explaining results to decision makers'],
    lessons: ['context-engineering', 'tools-integrations-workflows', 'verification-responsible-ai'],
    useCase: 'Ask for a problem’s objective and constraints as a formal model, then test it on a small case you can solve by hand.',
  },
};

export const isAiRole = (code: string | null | undefined): code is AiRoleCode => !!code && code in ROLE_AI_GUIDANCE;

export const lessonById = (id: string | null | undefined) => AI_LESSONS.find((l) => l.id === id) ?? null;

/** The lesson after this one, for the "Next lesson" link. */
export function nextLesson(id: string): AiLesson | null {
  const i = AI_LESSONS.findIndex((l) => l.id === id);
  return i < 0 ? null : AI_LESSONS[i + 1] ?? null;
}
