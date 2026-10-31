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
  /** Signal skill-gap card titles. */
  haveTitle: string;
  gapTitle: string;
  /** Loading screen's last status line, while roles are matched. */
  loadingMatch: string;
}

export const personaCopy: Record<PersonaKey, PersonaCopy> = {
  a: {
    interests: 'What are you into outside of class?',
    resume: 'Can you share your resume or project list?',
    resumeDrop: 'Upload resume, CV or project list (PDF)',
    skills: 'How confident are you in these skills?',
    roles: 'Which role do you want to aim for after graduating?',
    rolesLoading: 'Checking which roles fit you as AI grows…',
    haveTitle: 'Already yours',
    gapTitle: 'Learn next',
    loadingMatch: 'Checking how AI could shape roles that fit you',
  },
  b: {
    interests: 'What do you love doing outside of job hunting?',
    resume: 'Can you share your resume?',
    resumeDrop: 'Upload resume or LinkedIn PDF',
    skills: 'How strong are these skills for your first role?',
    roles: 'Which role do you want to go for first?',
    rolesLoading: 'Looking for roles that fit you as AI grows…',
    haveTitle: 'Skills you bring',
    gapTitle: 'Close the gap',
    loadingMatch: 'Finding roles that fit you across 3 AI futures',
  },
  c: {
    interests: 'What are you into outside of work?',
    resume: 'Can you share your resume or LinkedIn profile?',
    resumeDrop: 'Upload resume or LinkedIn PDF',
    skills: 'How strong are these skills in your work today?',
    roles: 'Which role do you want to grow into?',
    rolesLoading: 'Seeing how your role could shift with AI…',
    haveTitle: 'Transferable skills',
    gapTitle: 'Reskill next',
    loadingMatch: 'Seeing how your role could shift across 3 AI futures',
  },
};
