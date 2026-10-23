import type { PersonaKey } from './flows';

/**
 * Presentation-only copy per career stage (persona a/b/c from the Figma FLOWS page).
 * Nothing here is sent to the API: option meanings and payloads stay in flows.ts.
 * Prompts are short questions for Jobee's speech bubble.
 */
export interface PersonaCopy {
  /** Interests screen: what the learner is into, outside of work. */
  interests: string;
  /** Resume screen. */
  resume: string;
  /** Resume drop-zone label when nothing is uploaded yet. */
  resumeDrop: string;
  /** Skill check screen. */
  skills: string;
  /** Roles screen once matches are ready. */
  roles: string;
  /** Roles screen while matching. */
  rolesLoading: string;
  /** Signal screen: one short line above the three AI futures. */
  signalNote: string;
  /** Signal skill-gap card titles. */
  haveTitle: string;
  gapTitle: string;
  /** Loading screen's last status line, while roles are matched. */
  loadingMatch: string;
  /** Outcome screen: what Jobee helps this learner reach, shown mid-onboarding. */
  outcome: { say: string; goals: [string, string, string] };
}

export const personaCopy: Record<PersonaKey, PersonaCopy> = {
  a: {
    interests: 'What are you into outside of class?',
    resume: 'Can you share your resume or project list?',
    resumeDrop: 'Upload resume, CV or project list (PDF)',
    skills: 'How confident are you in these skills?',
    roles: 'Which role do you want to aim for after graduating?',
    rolesLoading: 'Checking which roles fit you as AI grows…',
    signalNote: 'Market signals, not headlines. Pick a possible future.',
    haveTitle: 'Already yours',
    gapTitle: 'Learn next',
    loadingMatch: 'Checking how AI could shape roles that fit you',
    outcome: {
      say: 'Here’s what you’ll know before you graduate!',
      goals: ['Which tech roles fit your skills', 'How AI could shift demand for them', 'What to learn next, step by step'],
    },
  },
  b: {
    interests: 'What do you love doing outside of job hunting?',
    resume: 'Can you share your resume?',
    resumeDrop: 'Upload resume or LinkedIn PDF',
    skills: 'How strong are these skills for your first role?',
    roles: 'Which role do you want to go for first?',
    rolesLoading: 'Looking for roles that fit you as AI grows…',
    signalNote: 'Explore demand for your first role across possible AI futures.',
    haveTitle: 'Skills you bring',
    gapTitle: 'Close the gap',
    loadingMatch: 'Finding roles that fit you across 3 AI futures',
    outcome: {
      say: 'Here’s what your job hunt could look like!',
      goals: ['Roles that fit the skills you have', 'Where demand is heading as AI grows', 'A clear plan to close your skill gaps'],
    },
  },
  c: {
    interests: 'What are you into outside of work?',
    resume: 'Can you share your resume or LinkedIn profile?',
    resumeDrop: 'Upload resume or LinkedIn PDF',
    skills: 'How strong are these skills in your work today?',
    roles: 'Which role do you want to grow into?',
    rolesLoading: 'Seeing how your role could shift with AI…',
    signalNote: 'How your role could shift as AI agents spread. Pick a possible future.',
    haveTitle: 'Transferable skills',
    gapTitle: 'Reskill next',
    loadingMatch: 'Seeing how your role could shift across 3 AI futures',
    outcome: {
      say: 'Here’s where your experience could take you!',
      goals: ['How your role could change with AI', 'Roles your skills already transfer to', 'A focused plan to reskill, one skill at a time'],
    },
  },
};
